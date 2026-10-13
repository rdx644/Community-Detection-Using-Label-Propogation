"""Metrics computed exclusively from the executed graph and saved partition."""

import networkx as nx
import numpy as np

from .lpa_engine import partition_sets, validate_partition
from .schemas import Metrics


def evaluate(graph: nx.Graph, memberships: dict[str, str], elapsed: float) -> Metrics:
    validate_partition(graph, memberships)
    groups = partition_sets(memberships)
    sizes = sorted(len(group) for group in groups)
    edges = graph.number_of_edges()
    modularity = None
    if edges:
        # Uniform scaling leaves weighted modularity unchanged and prevents its square
        # normalization from overflowing/underflowing for valid finite weights.
        normalized = graph.copy()
        total = sum(float(data.get("weight", 1.0)) for _, _, data in graph.edges(data=True))
        for _, _, data in normalized.edges(data=True):
            data["weight"] = float(data.get("weight", 1.0)) / total
        modularity = float(nx.community.modularity(normalized, groups, weight="weight"))
    internal = sum(memberships[a] == memberships[b] for a, b in graph.edges)
    return Metrics(
        nodes=len(graph),
        edges=edges,
        communities=len(groups),
        modularity=modularity,
        intra_community_edge_fraction=internal / edges if edges else None,
        minimum_community_size=min(sizes, default=0),
        median_community_size=float(np.median(sizes)) if sizes else 0.0,
        maximum_community_size=max(sizes, default=0),
        community_sizes=sizes,
        runtime_seconds=elapsed,
    )
