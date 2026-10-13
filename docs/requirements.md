# Requirements baseline — v1.0

Source: `reddit_academic_community_implementation_plan.md` (2026-10-14).
The user's React Bits instruction supersedes the blueprint's Streamlit recommendation.
This baseline freezes the six delivery phases before application implementation.

| ID | Requirement and acceptance criteria | Phase |
|---|---|---|
| R01 | CSV import, sample download, schema preview and explicit column mapping. Missing headers, unsupported encoding/type, oversized input and malformed CSV fail with actionable codes. | 2/4 |
| R02 | Validate identifiers, timezone-aware timestamps, positive finite weights and supported interaction types. Quarantine invalid rows with bounded reasons. Counts reconcile exactly. | 2 |
| R03 | Deduplicate events by ID or canonical fingerprint before aggregation; remove self-loops, preserve direction in normalized events, retain eligible isolates and deterministic graph ordering. | 2 |
| R04 | Filter timestamps, subreddit, interaction types, minimum aggregated edge weight and connected components explicitly. Provide weighted/unweighted runs and graph preview. | 2/4 |
| R05 | Run pinned NetworkX asynchronous weighted LPA with a recorded seed. Reject invalid graph inputs; handle empty, isolated, disconnected and tied-label graphs; every node is assigned exactly once. | 3 |
| R06 | Save node/edge/community counts, size distribution, weighted modularity (null without edges), intra-community edge fraction, measured runtime and multiseed pairwise ARI. | 3 |
| R07 | Explore an interactive bounded graph, search pseudonymous IDs, select communities and filter minimum size/subreddit. Large graphs use deterministic bounded summary mode. | 4 |
| R08 | Download memberships CSV, complete JSON result and analytical Markdown report; each carries the same run ID and provenance. Spreadsheet formula injection is escaped. | 3/4 |
| R09 | Fingerprint original bytes; save preprocessing/configuration, UTC time, Python/NetworkX/application versions, canonical membership hash and data-quality report. Fixed bytes/config/environment reproduce graph and memberships. | 3 |
| R10 | Enforce upload/row/graph/run retention/concurrency and subprocess timeout limits; support cancellation; preserve earlier successful artifacts; expose safe error states and request identifiers. | 5 |
| R11 | Pseudonymize user IDs by default, exclude text/raw IDs from public artifacts/logs, retain uploads in bounded memory with expiry, restrict CORS, and document deployment authentication boundary. | 5 |
| R12 | Unit, integration, regression, generated graph invariant, adversarial/security, frontend, real browser, lint/type, dependency/secret scans, startup and export checks pass. | 1–6 |
| R13 | Pinned locks, CI, one-unit production packaging, fresh-install smoke checks, reproducible sample/results/benchmark, user/algorithm/architecture documentation, traceability and release checklist. | 6 |

## Scope and user stories
Researchers import and validate data, configure a reproducible run, explore interaction
communities, compare seed sensitivity and export evidence. Evaluators can independently
verify saved metrics and reproduce the synthetic demonstration. Operators can limit work
and delete session artifacts. Data subjects' identifiers are minimized.

MVP plus weighted/time-windowed analysis and multiseed stability are required here.
Subreddit distributions interpret public discussion context separately from LPA;
they are not text-derived topic coherence or verified academic interests.
Live ingestion, identity inference, messaging, Louvain, temporal evolution and custom
iteration traces are deferred. No raw real Reddit dataset is published.

## Release gates
1. Contracts + schema + synthetic sample checks pass before ingestion implementation.
2. Deterministic ingestion/graph tests pass before LPA implementation.
3. Partition, metric, stability, timeout and export tests pass before UI integration.
4. Upload → configuration → exploration → exports passes in a real browser.
5. Full checks, independent metrics, resource limits and measured benchmark pass.
6. Fresh locked install + packaged startup + docs/traceability pass before GitHub push.

Target environment: Python 3.12, Node 22+; local single-user deployment. Initial bounds:
5 MiB, 50,000 events, 10,000 graph nodes, 50,000 edges, 60-second analysis deadline,
5 stability seeds, 400 rendered nodes/1,500 edges, 20 datasets/runs, 30-minute retention.
Benchmark target: 10,000 deterministic synthetic events complete within 60 seconds on
the recorded local host. This is a target, not a claim of measured performance.

Baseline review: lead-agent contract review against the source plan and explicit user
instructions. Product changes require a decision-log entry and contract/test updates.
