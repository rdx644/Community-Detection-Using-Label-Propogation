# Delivery backlog

- Phase 1: freeze R01–R13, schema/models, sample, dependency/CI setup; gate contracts.
- Phase 2 (depends 1): ingestion, quarantine, graph policies; gate data tests.
- Phase 3 (depends 2): LPA, metrics, ARI, provenance, exports; gate analytical tests.
- Phase 4 (depends 3): MCP registry components, React screens/API; gate browser workflow.
- Phase 5 (depends 4): job/retention/resource controls, integration/security/audits/benchmark.
- Phase 6 (depends 5): fresh install, release evidence/docs/checklist, commit/tag/push.

Each phase advances only after its relevant checks run successfully. Gate status and
actual verification evidence are recorded in `artifacts/verification/phase_gates.md`.
