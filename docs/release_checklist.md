# Release checklist — v1.0.0

## Requirements, data and algorithm
- [x] Baseline, user stories, contracts, assumptions and shared interfaces reviewed against plan.
- [x] Schema/data policies, graph aggregation, LPA tie-breaking and numeric limitations documented.
- [x] Every R01–R13 maps to implementation, tests and evidence in traceability.csv.
- [x] Valid, malformed, conflicting, duplicate, self-loop, timestamp and weight cases tested.
- [x] Quality counts reconcile; explicit graph filters retain eligible isolates.
- [x] Preview and execution select identical components, including equal-size ties.
- [x] LPA covers exactly every eligible node; empty/disconnected/generated graphs pass.
- [x] Independently checked modularity, undefined metrics, ARI and scaling regressions pass.
- [x] No unsupported iteration/convergence or verified-interest claims.

## Application and reliability
- [x] Real-browser import → configure → graph → evaluation → three exports passes.
- [x] Mapping, invalid-file recovery, previous successful result and filename preservation tested.
- [x] Display filters, visible-edge accounting and bounded benchmark graph tested.
- [x] Desktop/mobile visual checks and reduced-motion handling verified.
- [x] API owner isolation, chunked upload limit, capacity, cancellation and deadline tested.
- [x] Automatic expiry runs without subsequent requests; delete controls are available.
- [x] Pseudonyms/raw-text exclusion, spreadsheet injection and safe errors tested.
- [x] Atomic export failure preserves previous destination; saved artifact round-trips pass.

## Engineering and documentation
- [x] Frozen uv.lock, hashed requirements.lock and exact frontend package-lock verified.
- [x] Python/TypeScript lint, formatting and declared interface type checks pass.
- [x] 87 backend tests and four frontend tests pass; generated graph invariants included.
- [x] Bounded source secret scan and Python-runtime/Node dependency audits pass.
- [x] Fresh isolated Python/npm install, build, tests and real production smoke pass.
- [x] Actual results, hardware, benchmark, risks, limitations and reproducibility documented.
- [x] React Bits MCP search/inspection/install/audit evidence and license notices retained.
- [x] Native one-unit deployment and container packaging provided; CI repeats gates.
- [x] Application/source version marker: 1.0.0.

## External verification status
- Native production startup and real HTTP execution: **passed locally**.
- Docker build/runtime: **not run locally**, because Docker daemon is unavailable.
  The GitHub Actions workflow adds build and readiness gates for the container.
- GitHub push, release tag and remote CI result: recorded separately in the final delivery.
- Hosted public deployment: no provider/URL specified; deployment unit prepared, no hosted
  service claimed. A trusted authentication/rate-limiting proxy is required before exposure.

Evidence: `artifacts/verification/quality-gates.json`, `fresh-install.json`,
`production-smoke.json`, `browser-gate.json`, `benchmark.json` and `secret-scan.json`.
