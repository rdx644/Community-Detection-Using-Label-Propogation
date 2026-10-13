"""Application pipeline: domain modules, never UI state."""

import math
import time
import uuid
from dataclasses import replace

import networkx as nx

from .config import DEFAULT_LIMITS, Limits
from .evaluation import evaluate
from .graph_builder import GraphBuild, build_graph
from .lpa_engine import detect_communities
from .provenance import create_provenance, pseudonym
from .schemas import (
    AnalysisConfig,
    AnalysisResult,
    GraphEdge,
    GraphNode,
    GraphPreview,
    ValidatedDataset,
)
from .stability import compare_seeds
from .topic_analysis import summarize_subreddits


def graph_preview(
    graph: nx.Graph, memberships: dict[str, str], seed: int, limits: Limits
) -> GraphPreview:
    # Round-robin sampling retains visibility of small communities, not just hubs.
    groups: dict[str, list[str]] = {}
    for node, label in memberships.items():
        groups.setdefault(label, []).append(node)
    selected: list[str] = []
    for index in range(max((len(group) for group in groups.values()), default=0)):
        for label in sorted(groups):
            if index < len(groups[label]) and len(selected) < limits.preview_nodes:
                selected.append(groups[label][index])
        if len(selected) >= limits.preview_nodes:
            break
    visible = graph.subgraph(sorted(selected)).copy()
    # Bounded, reproducible circular groups are fast even when the analytic graph is large.
    labels = sorted({memberships[node] for node in selected})
    positions: dict[str, tuple[float, float]] = {}
    for group_index, label in enumerate(labels):
        center_angle = 2 * math.pi * group_index / max(1, len(labels)) - math.pi / 2
        center = (
            (0.62 * math.cos(center_angle), 0.62 * math.sin(center_angle))
            if len(labels) > 1
            else (0, 0)
        )
        nodes = sorted(node for node in selected if memberships[node] == label)
        for index, node in enumerate(nodes):
            # Golden angle avoids superimposed rings and does not invent graph edges.
            angle = index * math.pi * (3 - math.sqrt(5))
            radius = 0.27 * math.sqrt((index + 0.5) / len(nodes))
            positions[node] = (
                center[0] + radius * math.cos(angle),
                center[1] + radius * math.sin(angle),
            )
    edges = sorted(
        (min(a, b), max(a, b), data.get("weight", 1.0)) for a, b, data in visible.edges(data=True)
    )
    return GraphPreview(
        nodes=[
            GraphNode(
                id=node,
                community_id=memberships[node],
                degree=graph.degree(node),
                x=positions[node][0],
                y=positions[node][1],
            )
            for node in sorted(selected)
        ],
        edges=[
            GraphEdge(source=a, target=b, weight=weight)
            for a, b, weight in edges[: limits.preview_edges]
        ],
        truncated=len(visible) < len(graph) or len(edges) > limits.preview_edges,
    )


def analyze(
    dataset: ValidatedDataset,
    config: AnalysisConfig,
    limits: Limits = DEFAULT_LIMITS,
    run_id: str | None = None,
) -> AnalysisResult:
    start = time.perf_counter()
    # Use the preview's source-ID policy before display pseudonymization.
    original = build_graph(dataset.events, config, limits)
    names = {
        user: pseudonym(user, dataset.fingerprint)
        for event in dataset.events
        for user in (event.source_user, event.target_user)
    }
    events = tuple(
        replace(
            event,
            source_user=names[event.source_user],
            target_user=names[event.target_user],
            text="",
        )
        for event in original.events
    )
    build = GraphBuild(nx.relabel_nodes(original.graph, names, copy=True), original.summary, events)
    memberships = detect_communities(build.graph, config.seed, config.weighted)
    stability = compare_seeds(build.graph, config.stability_seeds, config.weighted)
    communities = summarize_subreddits(build.events, memberships)
    preview = graph_preview(build.graph, memberships, config.seed, limits)
    metrics = evaluate(build.graph, memberships, 0)
    provenance = create_provenance(dataset, memberships)
    metrics.runtime_seconds = time.perf_counter() - start
    warnings = []
    if dataset.quality.rejected_rows:
        warnings.append(f"{dataset.quality.rejected_rows} invalid rows were quarantined.")
    if dataset.quality.duplicate_rows or dataset.quality.self_loops:
        warnings.append("Duplicate events and self-loops were removed before analysis.")
    if build.summary.isolates:
        warnings.append(f"{build.summary.isolates} isolates are retained as singleton communities.")
    if not build.graph:
        warnings.append("No nodes match the selected filters; metrics without edges are undefined.")
    if preview.truncated:
        warnings.append(
            "Graph display is a bounded summary; metrics and exports cover the full graph."
        )
    return AnalysisResult(
        run_id=run_id or str(uuid.uuid4()),
        status="completed_with_warnings" if warnings else "success",
        config=config,
        quality=dataset.quality,
        summary=build.summary,
        memberships=memberships,
        communities=communities,
        metrics=metrics,
        stability=stability,
        graph=preview,
        provenance=provenance,
        warnings=warnings,
    )
