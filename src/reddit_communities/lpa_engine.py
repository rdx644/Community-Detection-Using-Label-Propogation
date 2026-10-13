"""Pinned asynchronous label propagation, with explicit partition invariants."""

import math
from collections import defaultdict

import networkx as nx

from .errors import AnalysisError


def validate_graph(graph: nx.Graph) -> None:
    if graph.is_directed() or graph.is_multigraph() or nx.number_of_selfloops(graph):
        raise AnalysisError("INVALID_GRAPH", "LPA requires a simple undirected graph without loops")
    for _, _, data in graph.edges(data=True):
        weight = data.get("weight", 1.0)
        if not isinstance(weight, (float, int)) or not math.isfinite(weight) or weight <= 0:
            raise AnalysisError(
                "INVALID_GRAPH_WEIGHT", "All graph weights must be finite and positive"
            )
    try:
        total = math.fsum(float(data.get("weight", 1)) for _, _, data in graph.edges(data=True))
        if not math.isfinite(total * 2):
            raise OverflowError
    except OverflowError as error:
        raise AnalysisError(
            "WEIGHT_OVERFLOW", "Graph total weight exceeds numeric limits"
        ) from error


def validate_partition(graph: nx.Graph, memberships: dict[str, str]) -> None:
    if set(memberships) != set(graph) or any(not label for label in memberships.values()):
        raise AnalysisError("INVALID_PARTITION", "Partition must cover exactly all eligible nodes")


def partition_sets(memberships: dict[str, str]) -> list[set[str]]:
    groups: dict[str, set[str]] = defaultdict(set)
    for node, label in memberships.items():
        groups[label].add(node)
    return [groups[label] for label in sorted(groups)]


def detect_communities(graph: nx.Graph, seed: int, weighted: bool = True) -> dict[str, str]:
    validate_graph(graph)
    if not graph:
        return {}
    ordered: nx.Graph = nx.Graph()
    ordered.add_nodes_from(sorted(graph.nodes))
    ordered.add_edges_from(
        sorted(
            (min(a, b), max(a, b), {"weight": float(data.get("weight", 1.0))})
            for a, b, data in graph.edges(data=True)
        )
    )
    try:
        groups = sorted(
            sorted(group)
            for group in nx.community.asyn_lpa_communities(
                ordered, weight="weight" if weighted else None, seed=seed
            )
        )
    except nx.NetworkXException as error:
        raise AnalysisError("ALGORITHM_FAILED", "Label propagation could not complete") from error
    flattened = [node for group in groups for node in group]
    if len(flattened) != len(set(flattened)) or any(not group for group in groups):
        raise AnalysisError("INVALID_PARTITION", "Algorithm produced overlapping or empty groups")
    memberships = {node: f"C{index:03d}" for index, group in enumerate(groups, 1) for node in group}
    memberships = dict(sorted(memberships.items()))
    validate_partition(ordered, memberships)
    return memberships
