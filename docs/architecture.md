# Architecture and frozen interfaces

One deployable modular monolith: FastAPI serves a built React SPA and `/api/v1`.
React calls typed HTTP interfaces; it contains no graph construction or LPA logic.
Python modules depend on schemas, never on frontend state or HTTP handlers.

Pipeline: ingestion → validation/preprocessing → graph_builder → lpa_engine →
evaluation/stability → provenance/exports. The application service owns bounded
in-memory datasets/results and subprocess job lifetime; API only adapts transport.

## Public Python interfaces
- `ingest_csv(data: bytes, filename: str, mapping: dict[str,str] | None) -> ValidatedDataset`
- `build_graph(events: tuple[Event,...], config: AnalysisConfig) -> GraphBuild`
- `detect_communities(graph: nx.Graph, seed: int, weighted: bool) -> dict[str,str]`
- `evaluate(graph: nx.Graph, memberships: dict[str,str], elapsed: float) -> Metrics`
- `compare_seeds(graph, seeds, weighted) -> StabilityResult`
- `analyze(dataset: ValidatedDataset, config: AnalysisConfig) -> AnalysisResult`
- `export_memberships(result) -> bytes`; `export_report(result) -> str`
- `run_with_timeout(dataset, config, timeout_seconds) -> AnalysisResult`

## HTTP contract v1
GET `/health`: readiness/version. GET `/sample`: synthetic CSV.
POST `/datasets` multipart `file` and optional JSON `mapping`: validated dataset preview,
quality, ID, available filters and fingerprint (201). No raw IDs/text are returned.
POST `/datasets/{id}/preview` config: bounded graph size/count preview.
POST `/runs` `{dataset_id,config}`: asynchronous job `{run_id,status}` (202).
GET `/runs/{id}`: job status plus result on success; sanitized error on failure.
DELETE `/runs/{id}`: cancellation or deletion (204). DELETE `/datasets/{id}`: deletion.
GET `/runs/{id}/exports/{memberships.csv|result.json|report.md}`: saved artifacts.
All state-bearing endpoints require a browser-session UUID `X-Session-ID`, with owner
checks and TTL. UI creates the UUID and holds it in sessionStorage. This isolates local
sessions; it is not authentication for a public deployment.

Errors: `{error:{code,message,details},request_id}`. HTTP 400 malformed CSV/mapping;
422 schema/row/config invalid; 413 file/row/graph limits; 404 missing/expired/other-owner
artifact; 409 not ready; 429 capacity; 504 deadline. Errors expose no traceback/paths.
Terminal statuses: success, completed_with_warnings, failed, cancelled. Internal queued
and running statuses are not analytical success. Failed runs never replace successful ones.

No database/external queue or Reddit credentials. Production binds loopback by default;
public hosting needs a trusted authentication/rate-limiting proxy. A bounded child process
provides a real killable deadline. API worker count must be 1 for in-memory job ownership.
