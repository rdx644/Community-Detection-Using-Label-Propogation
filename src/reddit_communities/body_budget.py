"""Bound request streams before multipart parsing, including chunked uploads."""

import uuid

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class BodyBudgetMiddleware:
    def __init__(self, app: ASGIApp, maximum: int) -> None:
        self.app = app
        self.maximum = maximum

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return
        chunks: list[Message] = []
        total = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            total += len(message.get("body", b""))
            if total > self.maximum:
                request_id = str(uuid.uuid4())
                response = JSONResponse(
                    {
                        "error": {
                            "code": "REQUEST_LIMIT",
                            "message": "Request exceeds upload budget",
                            "details": {},
                        },
                        "request_id": request_id,
                    },
                    status_code=413,
                    headers={
                        "X-Request-ID": request_id,
                        "Cache-Control": "no-store",
                        "X-Content-Type-Options": "nosniff",
                    },
                )
                await response(scope, receive, send)
                return
            chunks.append(message)
            if not message.get("more_body", False):
                break
        index = 0

        async def replay() -> Message:
            nonlocal index
            if index < len(chunks):
                item = chunks[index]
                index += 1
                return item
            return await receive()

        await self.app(scope, replay, send)
