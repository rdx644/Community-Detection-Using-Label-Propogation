# Phase-gate test plan

1. Contract: model validation, schema/header sample, unique IDs and timestamp/weight rules.
2. Data: malformed encodings/CSV/header/row limits, quarantine count equation, conflicts,
   duplicate fingerprint, self-loops, UTC equivalence, sum overflow, deterministic filtering.
3. Engine: empty/single/isolate/clique/path/bridged/disconnected/tied/weighted/hub fixtures,
   seeded generated graphs, independent modularity, partition/ARI invariants, exports.
4. UI: typed build, component tests, real-browser sample + custom mapped upload, invalid
   file/error state, configuration, polling, search/filter, exports and responsive viewport.
5. Hardening: real subprocess timeout/cancellation, owner isolation, TTL/capacity/limits,
   formula/XSS upload, sanitized errors, preserved successful artifacts, locks/audits/scans.
6. Release: fresh locked Python+Node install, built SPA/startup endpoints and real worker,
   benchmark and artifact round-trip; GitHub CI uses equivalent mandatory checks.

Evidence belongs in `artifacts/verification/`, with commands, actual output and timestamps.
Never infer passing checks from code review. Unavailable infrastructure is recorded as
unverified. Targets and measured results must be distinguished.
