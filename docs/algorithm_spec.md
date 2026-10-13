# Algorithm specification v1

For node v and neighboring label l, support is `S_v(l) = Σ_(u∈N(v)) w_uv × 1[L(u)=l]`.
Each asynchronous update adopts a maximal-support label under the tie rule below.
Unweighted mode uses unit edge weights after the same aggregation/threshold policy.

Weighted modularity is `Q = Σ_c [L_c/m − (K_c/(2m))²]`, where L_c is the total internal
edge weight counted once, K_c is the sum of weighted degrees in community c, and m is
total undirected edge weight. NetworkX computes it on the actual partition. A common
uniform weight rescaling prevents square-normalization overflow/underflow and preserves Q.

Primary algorithm: `networkx.algorithms.community.asyn_lpa_communities`.
Sorted node/edge insertion and pinned NetworkX version plus integer seed define repeatable
asynchronous update order. Weighted support is the sum of incident weights for each
neighbor label. NetworkX shuffles node order on each pass; it retains the current label
when it is among maxima, otherwise randomly selects a maximal label using the seeded RNG.
No iteration count or custom convergence trace is exposed.

Only simple undirected graphs with finite positive weights and no self-loops are accepted.
Empty graphs return empty memberships; isolates receive singleton communities.
Canonical community IDs `C001…` are assigned after sorting each group and sorting groups
lexicographically, so random generator output order does not change identifiers.
Validate that groups are disjoint, nonempty and cover precisely the input nodes.

Weighted modularity uses NetworkX on the same configured graph. Edgeless modularity and
intra-community fraction are null; the latter counts unweighted internal edges / all edges.
Sizes use min/median/max and per-community counts. Runtime measures actual application
analysis time, excluding process startup/HTTP transport. Pairwise adjusted Rand index is
computed for up to five distinct configured seeds; the denominator uses all eligible nodes.
Degenerate equal partitions have ARI=1. Label names do not affect ARI.

Separate interpretation: subreddit participation distributions per detected community.
This is observable discussion context, not expertise or text/topic coherence. No personal
attributes, objective ground-truth correctness or universally optimal partition is claimed.

References: [NetworkX asynchronous LPA](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.label_propagation.asyn_lpa_communities.html)
and the installed pinned source, reviewed before engine implementation.
