"""Thin HTTP adapters; built React frontend and analysis deploy as one unit."""

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, Header, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from . import __version__
from .body_budget import BodyBudgetMiddleware
from .config import DEFAULT_LIMITS, Limits
from .errors import AnalysisError
from .exports import export_memberships, export_report
from .schemas import AnalysisConfig, DatasetView, GraphSummary, RunRequest, RunView
from .service import AnalysisService

ROOT = Path(__file__).resolve().parents[2]
Owner = Annotated[uuid.UUID, Header(alias="X-Session-ID")]
log = logging.getLogger("reddit_communities")


def create_app(limits: Limits = DEFAULT_LIMITS) -> FastAPI:
    service = AnalysisService(limits)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        async def cleanup_expired() -> None:
            while True:
                await asyncio.sleep(max(0.05, min(30, limits.retention_seconds)))
                service.prune()

        janitor = asyncio.create_task(cleanup_expired())
        try:
            yield
        finally:
            janitor.cancel()
            with suppress(asyncio.CancelledError):
                await janitor
            await run_in_threadpool(service.close)

    app = FastAPI(
        title="Reddit Academic Community Intelligence", version=__version__, lifespan=lifespan
    )
    app.state.service = service

    @app.middleware("http")
    async def resource_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        length = request.headers.get("content-length")
        if length and (not length.isdigit() or int(length) > limits.upload_bytes + 65_536):
            return JSONResponse(
                {
                    "error": {
                        "code": "REQUEST_LIMIT",
                        "message": "Request exceeds upload budget",
                        "details": {},
                    },
                    "request_id": request_id,
                },
                status_code=413,
            )
        try:
            response = await call_next(request)
        except Exception:
            # HTTP recovery boundary: log only a request ID, never arbitrary exception/raw input.
            log.error("Unhandled request failure id=%s", request_id)
            response = JSONResponse(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Request failed safely",
                        "details": {},
                    },
                    "request_id": request_id,
                },
                status_code=500,
            )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; connect-src 'self'; frame-ancestors 'none'; "
            "base-uri 'self'; form-action 'self'"
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(AnalysisError)
    async def domain_error(request: Request, error: AnalysisError) -> JSONResponse:
        return JSONResponse(
            {"error": error.payload(), "request_id": request.state.request_id},
            status_code=error.status,
        )

    @app.exception_handler(RequestValidationError)
    async def contract_error(request: Request, error: RequestValidationError) -> JSONResponse:
        locations = [".".join(str(part) for part in issue["loc"]) for issue in error.errors()]
        return JSONResponse(
            {
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "Check the input format and configuration fields",
                    "details": {"fields": locations},
                },
                "request_id": request.state.request_id,
            },
            status_code=422,
        )

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ready", "version": __version__}

    @app.get("/api/v1/sample")
    def sample() -> FileResponse:
        return FileResponse(
            ROOT / "data/sample/sample_interactions.csv",
            media_type="text/csv",
            filename="synthetic_sample_interactions.csv",
        )

    @app.post("/api/v1/datasets", status_code=201, response_model=DatasetView)
    async def upload(
        owner: Owner,
        file: Annotated[UploadFile, File()],
        mapping: Annotated[str | None, Form()] = None,
    ) -> dict[str, object]:
        raw = await file.read(limits.upload_bytes + 1)
        await file.close()
        parsed = None
        if mapping:
            try:
                parsed = json.loads(mapping)
                if not isinstance(parsed, dict) or any(
                    not isinstance(key, str) or not isinstance(value, str)
                    for key, value in parsed.items()
                ):
                    raise ValueError
            except (ValueError, TypeError) as error:
                raise AnalysisError(
                    "INVALID_MAPPING", "Column mapping must be a JSON object", 400
                ) from error
        return await run_in_threadpool(service.upload, raw, file.filename or "", str(owner), parsed)

    @app.post("/api/v1/datasets/{identifier}/preview", response_model=GraphSummary)
    def preview(identifier: str, owner: Owner, config: AnalysisConfig) -> GraphSummary:
        return service.preview(identifier, str(owner), config)

    @app.delete("/api/v1/datasets/{identifier}", status_code=204)
    def delete_dataset(identifier: str, owner: Owner) -> Response:
        service.delete_dataset(identifier, str(owner))
        return Response(status_code=204)

    @app.post("/api/v1/runs", response_model=RunView, status_code=202)
    def start_run(body: RunRequest, owner: Owner) -> RunView:
        return service.start(body.dataset_id, str(owner), body.config)

    @app.get("/api/v1/runs/{identifier}", response_model=RunView)
    def get_run(identifier: str, owner: Owner) -> RunView:
        return service.get_run(identifier, str(owner))

    @app.delete("/api/v1/runs/{identifier}", status_code=204)
    def delete_run(identifier: str, owner: Owner) -> Response:
        service.delete_run(identifier, str(owner))
        return Response(status_code=204)

    @app.get("/api/v1/runs/{identifier}/exports/{format}")
    def export(identifier: str, format: str, owner: Owner) -> Response:
        result = service.get_run(identifier, str(owner)).result
        if result is None:
            raise AnalysisError("NOT_READY", "Exports become available after a successful run", 409)
        if format == "memberships.csv":
            content, media_type = export_memberships(result), "text/csv"
        elif format == "result.json":
            content, media_type = result.model_dump_json(indent=2).encode(), "application/json"
        elif format == "report.md":
            content, media_type = export_report(result).encode(), "text/markdown"
        else:
            raise AnalysisError(
                "EXPORT_FORMAT", "Choose memberships.csv, result.json or report.md", 400
            )
        return Response(
            content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{result.run_id}-{format}"'},
        )

    app.add_middleware(BodyBudgetMiddleware, maximum=limits.upload_bytes + 65_536)
    dist = ROOT / "frontend/dist"
    if dist.is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/", include_in_schema=False)
        def index() -> FileResponse:
            return FileResponse(dist / "index.html")

    return app


app = create_app()
