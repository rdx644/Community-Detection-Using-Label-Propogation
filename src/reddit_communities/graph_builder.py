"""Deterministic, explicit undirected graph policy."""

import math
from collections import defaultdict
from dataclasses import dataclass

import networkx as nx

from .config import DEFAULT_LIMITS, Limits
from .errors import AnalysisError
from .schemas import AnalysisConfig, Event, GraphSummary


@dataclass(frozen=True)
class GraphBuild:
    graph: nx.Graph
    summary: GraphSummary
    events: tuple[Event, ...]


def build_graph(
    events: tuple[Event, ...], config: AnalysisConfig, limits: Limits = DEFAULT_LIMITS
) -> GraphBuild:
    selected = tuple(
        event
        for event in events
        if (
            (config.start_time is None or event.timestamp >= config.start_time)
            and (config.end_time is None or event.timestamp <= config.end_time)
            and event.interaction_type in config.interaction_types
            and (not config.subreddits or event.subreddit in config.subreddits)
        )
    )
    graph: nx.Graph = nx.Graph()
    graph.add_nodes_from(
        sorted({user for event in selected for user in (event.source_user, event.target_user)})
    )
    if len(graph) > limits.graph_nodes:
        raise AnalysisError("GRAPH_LIMIT", "Selected graph exceeds the supported node budget", 413)
    weights: dict[tuple[str, str], list[float]] = defaultdict(list)
    for event in selected:
        a, b = sorted((event.source_user, event.target_user))
        if a == b or not math.isfinite(event.weight) or event.weight <= 0:
            raise AnalysisError(
                "INVALID_GRAPH_EVENT", "Graph events require positive valid weights"
            )
        weights[a, b].append(event.weight)
    removed = 0
    for (a, b), values in sorted(weights.items()):
        try:
            weight = math.fsum(values)
        except OverflowError as error:
            raise AnalysisError(
                "WEIGHT_OVERFLOW", "Aggregated edge weight exceeds numeric limits"
            ) from error
        if not math.isfinite(weight):
            raise AnalysisError("WEIGHT_OVERFLOW", "Aggregated edge weight exceeds numeric limits")
        if weight < config.minimum_weight:
            removed += 1
        else:
            graph.add_edge(a, b, weight=weight if config.weighted else 1.0)
    if graph.number_of_edges() > limits.graph_edges:
        raise AnalysisError("GRAPH_LIMIT", "Selected graph exceeds the supported edge budget", 413)
    removed_nodes = 0
    if config.largest_component_only and graph:
        components = sorted(
            (sorted(group) for group in nx.connected_components(graph)),
            key=lambda group: (-len(group), group),
        )
        removed_nodes = len(graph) - len(components[0])
        graph = graph.subgraph(components[0]).copy()
    try:
        total = math.fsum(float(data["weight"]) for _, _, data in graph.edges(data=True))
        if not math.isfinite(total) or not math.isfinite(2 * total):
            raise OverflowError
    except OverflowError as error:
        raise AnalysisError(
            "WEIGHT_OVERFLOW", "Total graph weight exceeds numeric limits"
        ) from error
    summary = GraphSummary(
        nodes=len(graph),
        edges=graph.number_of_edges(),
        isolates=nx.number_of_isolates(graph),
        connected_components=nx.number_connected_components(graph),
        selected_events=len(selected),
        filtered_events=len(events) - len(selected),
        threshold_removed_edges=removed,
        component_removed_nodes=removed_nodes,
        total_edge_weight=total,
    )
    return GraphBuild(graph, summary, selected)
