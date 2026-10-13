# Deployment and verification

## Verified native single-unit deployment
Python 3.12 + Node 22+ + uv. `uv sync --frozen`; `npm ci` and `npm run build`
in frontend; `uv run python app.py`. The FastAPI process serves the built SPA and API
at http://127.0.0.1:8000. One API worker is mandatory: state is held in process memory.
Set RACI_HOST/RACI_PORT to change the binding. Uvicorn caps concurrent requests at 32;
the service permits two killable analysis workers, each with a 60-second deadline.

`uv run python scripts/smoke_test.py` starts a production server on a free loopback port,
uploads the sample, executes an actual child worker and checks all exported artifacts.
`uv run python scripts/browser_gate.py` performs the UI workflow with Playwright CLI.

## Container package
`docker build -t community-observatory .`

`docker run --rm -p 127.0.0.1:8000:8000 --memory=1g --cpus=2 community-observatory`

The multi-stage build uses locked dependencies, includes only the built UI in the runtime,
runs without root and has an HTTP readiness check. The local Docker engine was unavailable,
so local container execution is unverified. GitHub CI builds and checks container readiness.
Native production execution is the locally verified deployment gate.

## Public hosting boundary
No cloud provider or public URL was requested. This release prepares a deployment unit;
it does not claim a hosted deployment. Before exposing it publicly, put it behind a trusted
authentication and request-rate-limiting proxy, HTTPS, and container CPU/memory limits.
X-Session-ID isolates local sessions; it is a capability token, not account authentication.
No wildcard CORS policy is enabled. The app uses same-origin API requests and self-hosted fonts.

Uploaded datasets and saved runs expire after 30 minutes, with physical cleanup every
30 seconds at most. They are also deleted on process shutdown/restart. Active workers
finish/cancel within their timeout and are terminated on shutdown. No raw data is written
to persistent application storage. Multipart parsing may spool larger uploads to transient
OS temporary files; each upload file is closed immediately after bounded reading. Downloads
are retained by the researcher's browser and must be
deleted separately. Metrics and pseudonyms can still be sensitive research data.

## Release gates
Locked install, contracts, lint/format/types, unit/integration/security/regression suites,
source secret scan, dependency audits, real browser, actual benchmark, native startup
and export round-trip must pass before push. CI repeats those checks and adds the Linux
container gate. Remote CI success must be observed separately; local success is not
reported as remote CI success.
