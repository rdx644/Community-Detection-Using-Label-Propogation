# Risks and mitigations

| Risk | Likelihood / impact | Mitigation and check | Owner |
|---|---|---|---|
| Dirty/duplicate events | high/high | quarantine reconciliation and dedup tests | lead |
| Nondeterminism | medium/high | pinned locks, sorted graph, fixed seed repeat tests | lead |
| Misinterpreted academic interest | high/high | separate subreddit context, UI caveat | lead |
| Unbounded upload or long LPA | medium/high | byte/row/graph limits, killed worker timeout | lead |
| Identifier/content disclosure | medium/high | scoped pseudonyms, no raw exports/logs, owner tests | lead |
| Exposed public deployment | medium/high | documented trusted auth proxy, no public default | lead |
| Export spreadsheet injection | medium/high | prefix dangerous cells, adversarial regression | lead |
| In-memory state loss | medium/medium | TTL notice, immediate downloads, documented single worker | lead |
| Large SVG graphs | medium/medium | bounded deterministic graph display and warnings | lead |
| Docker engine unavailable | observed/medium | native packaged production gate; container remains unverified | lead |
