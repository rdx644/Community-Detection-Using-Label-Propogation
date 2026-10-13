# Known limitations and future scope

- LPA is stochastic; seed stability does not establish validity or academic expertise.
- The synthetic sample and benchmark are engineering fixtures, not empirical Reddit
  findings. No claim of real-world academic-interest detection is made.
- Subreddit incidence is discussion context, not NLP topic extraction/coherence. Text
  models, Louvain comparison, time evolution and live ingestion are deferred.
- Double-precision weights and modularity have numeric limits. Overflow is rejected;
  modularity uses uniformly scaled weights to prevent normalization overflow/underflow.
- In-memory sessions require one API worker. There is no durable account/database store.
  Reloading the page does not recover the interactive state; download results promptly.
- Uploaded public usernames are pseudonymized with a dataset-scoped, exposed fingerprint.
  They remain vulnerable to guessing; this is minimization, not guaranteed anonymization.
- Visualization is bounded and laid out by community, not an instrumented LPA history
  or a measured social distance. Exports/metrics cover the full analytical graph.
- Native production startup is locally tested. Docker is unavailable locally; container
  execution is gated in CI and must be observed after push. No hosted URL is provisioned.
- The pinned Starlette test client currently emits a deprecation warning for httpx;
  real HTTP smoke checks also run. This is not a test failure.
- Benchmark memory is Python allocations measured with tracemalloc, not total RSS/native
  allocation; tracing adds timing overhead. Targets are tied to the recorded host/fixture.

No known critical correctness/data-integrity defects remain after the recorded gates.
An unavailable verification environment is recorded rather than treated as a passing check.
