# Decision log

- D01 (2026-10-14): Use React + React Bits in place of Streamlit per explicit user request.
  FastAPI serves SPA and analysis in one unit, retaining modular-monolith boundaries.
- D02: Use the supplied `C:\Users\putit\.codex\mcp\config.toml` shadcn stdio server;
  configure free `@react-bits` registry in frontend/components.json. Do not alter global
  Codex configuration or imply a server is preconnected when it is not.
- D03: Quarantine invalid rows but reject fatal schema/CSV failures; report reconciled counts.
- D04: Keep threshold-induced isolates as singletons; case-sensitive IDs; stable ordering.
- D05: Session-scoped memory, bounded retention and killable workers; single API worker.
- D06: Default pseudonyms and no raw dataset persistence. Synthetic-only committed artifacts.
- D07: Implement multiseed ARI and subreddit context now; defer live data and text models.
- D08: Prepare deployment package and local production smoke gate; do not claim a hosted
  deployment when no hosting target has been specified. Push to the user's supplied repo.
- D09: Record source-header mappings and preprocessing policy in provenance; generate
  frontend types from OpenAPI and enforce a schema drift regression test.
- D10: Remove the shadcn generator from installed app dependencies after MCP-guided source
  installation; its braces dependency had an unpatched high advisory. Runtime and retained
  development dependencies pass the recorded audits. Supplied MCP config remains unchanged.
- D11: Uniformly rescale weights only for NetworkX modularity normalization; graph weights,
  primary LPA and exports retain configured values. Extreme scaling regression checks Q.
- D12: Use bounded session memory rather than disk persistence; a background janitor enforces
  physical expiry even when no further requests arrive.
- D13: Apply graph/component policy before pseudonymization, so lexical ties select the
  same component during preview and execution; add tied-component regression fixtures.
