# Trust boundaries and operational safeguards

Scope: local browser → same-origin HTTP API → validated in-memory events → killable
analysis process → saved pseudonymous artifacts → browser downloads. This is a local
single-user research tool; public account authentication is outside the release boundary.

Untrusted CSV/header/mapping/config inputs cannot execute code. Strict UTF-8/CSV parsing,
schema checks, finite positive weights and byte/row/field/graph limits protect analysis.
The ASGI middleware bounds request streams before multipart parsing, including chunked
uploads. Runtime/concurrency/retention budgets bound jobs and stored data.

Session UUIDs provide capability-based owner isolation; knowing another session UUID
would grant access. A trusted authentication proxy is required before public exposure.
No wildcard CORS exists; CSP forbids external scripts, frames and arbitrary connections.
Errors omit tracebacks, invalid secret-like values and filesystem paths; logs contain
request IDs only. Uploaded IDs/text never enter the browser result or source-controlled
artifacts. Larger multipart uploads may use transient OS temporary files, closed after
bounded reading; normalized session data is not persisted. React escapes displayed
metadata. CSV formula prefixes are escaped defensively.

Workers are terminated on deadline/cancellation/shutdown. Background cleanup removes
expired uploads/results without waiting for further user requests. Explicit delete endpoints
remove uploads and successful runs. Failed analyses do not modify earlier saved results.
Atomic file exports preserve previous contents when replacement fails.

Verification: `tests/security/test_reliability.py`, `tests/integration/test_api.py`,
`tests/integration/test_pipeline.py`, bounded detect-secrets scan, pip-audit and npm audit.
Deployment adds HTTPS, trusted authentication, rate controls and OS/container memory limits.
