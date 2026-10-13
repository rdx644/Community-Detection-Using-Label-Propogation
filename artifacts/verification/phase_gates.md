# Phase gate evidence

Host: Windows, Python 3.12.10, Node 26.3.0. Source plan dated 2026-10-14 local time.

## Phase 1 — passed
Frozen requirements, data/HTTP/Python interfaces, algorithm policies, risks and backlog
written before ingestion implementation. `uv run pytest tests/unit/test_contracts.py -q`:
**11 passed**. Deterministic synthetic sample: 267 valid events, 48 synthetic users.

## Phase 2 — passed
`uv run pytest tests/unit -q`: **36 passed**. `uv run ruff check .`: passed.
`uv run ruff format --check .`: 21 files formatted. `uv run mypy`: no issues in 8 modules.
Tests cover quarantine reconciliation, exact/event-ID conflicts, fingerprint/timezones,
row/byte/node limits, malformed files, self-loops, filters, isolates and numeric overflow.
Two interface annotation issues were found and corrected before advancing.

## MCP connection
The supplied config's `npx shadcn@latest mcp` was launched via the official MCP SDK stdio
transport. Initialization and tool discovery succeeded; schemas are in `mcp-tools.json`.
React Bits registry is configured in `frontend/components.json`.

## Phase 3 — passed
68 backend tests passed; lint, formatting and mypy passed in 16 analytical modules.
Hand-checkable and generated graph fixtures, seeded repeatability, independent modularity,
pairwise ARI, JSON/CSV round-trip and real subprocess timeout/cancellation were executed.

## Phase 4 — passed
React typed production build, ESLint and four frontend tests pass. Playwright CLI ran the
five-view researcher workflow using the actual Python API/worker. Sample: 48 users,
267 edges, four communities of 12, Q=0.7495420905, mean ARI=1.0.
Desktop/mobile evidence, three downloads, mapped upload and invalid-file recovery are saved.

## Phase 5 — passed
Final suite: **87 backend tests**, including unit/integration/security/regression and
generated graph invariants. Owner/TTL/capacity/stream limits, safe errors, cancellation,
successful artifact preservation and atomic exports pass. Source secret scan: zero findings.
Python-runtime pip-audit and full Node npm audit: no known vulnerabilities.
Benchmark: 10,000 events / 1,000 nodes / 9,093 edges, 3.198873-second wall time, measured
peak traced Python allocation 15.735914 MiB, below the 60-second declared budget.
Real browser also explored the bounded 400-node / 1,379-edge benchmark display.

Confirmed defects fixed with regression evidence: implicit unit-weight graph display,
extreme modularity normalization, filtered visible-edge counter, previous dataset label,
and largest-component lexical ties differing between preview and execution.

## Phase 6 — passed locally
All 11 recorded quality commands returned zero. A fresh isolated source copy installed
from uv.lock and npm lock, passed backend/frontend suites, built the SPA and ran the actual
native HTTP workflow/export checks. Docs, traceability, sample exports and license notices
are included. Local Docker daemon is unavailable; container execution is gated in CI and
is not represented as locally passed. GitHub push/remote CI status is reported separately.
