# Actual benchmark and demonstration

Recorded at **2026-10-13 21:27:50 UTC** (2026-10-14 local time).
Source evidence: `artifacts/verification/benchmark.json`.

Environment: Windows 11 build 26200, Python 3.12.10, NetworkX 3.7,
12th Gen Intel Core i3-1215U, eight logical CPUs. Deterministic generator seed 2026.
Analysis seed 42; weighted; minimum edge weight 0.1; stability seeds 42, 7, 21.

| Measurement | Synthetic demonstration | Synthetic benchmark |
|---|---:|---:|
| Input events | 267 | 10,000 |
| Eligible nodes | 48 | 1,000 |
| Aggregated edges | 267 | 9,093 |
| Communities | 4 | 10 |
| Community sizes | 12 each | 100 each |
| Weighted modularity | 0.7495420905 | 0.8999710336 |
| Internal-edge fraction | 0.9887640449 | 1.0 |
| Actual analysis runtime | 0.010122 s | 2.697888 s |

Benchmark ingestion + analysis wall time: **3.198873 seconds**, below the declared
**60-second** gate. Peak traced Python allocation: **15.735914 MiB**. This is one
recorded measurement with tracemalloc enabled, not total RSS or a statistical average;
tracing affects runtime. Host load and environment can change these results.

Benchmark CSV: 1,036,972 bytes; SHA-256:
`fea34f9d3a7cdd85d35595edc87753d94c8b3c07389df06de35078b96fa4fb39`.
Repeated execution produced identical memberships under fixed configuration.

The browser gate also ran the benchmark through the real application. The 1,000-node
result displayed a bounded 400-node, 1,379-edge summary and supported community selection.
Its 2.017-second CLI interaction measurement includes CLI startup and accessibility
snapshots; it is not a pure browser render-time measurement.

The demonstration's mean pairwise ARI is 1.0 on the recorded three seeds. Its complete
artifact, memberships, quality report and Markdown report are in `artifacts/sample/`.
These are synthetic engineering results. They do not validate claims about real Reddit
communities, academic interests or expertise.

Reproduce: `uv run python scripts/benchmark.py` regenerates actual JSON evidence and
synthetic result exports. `uv run python scripts/browser_gate.py` regenerates browser
evidence. Compare fingerprint/membership hashes; run IDs, timestamps and runtimes vary.
