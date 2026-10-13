import math

import networkx as nx
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from reddit_communities.analysis import graph_preview
from reddit_communities.config import DEFAULT_LIMITS
from reddit_communities.errors import AnalysisError
from reddit_communities.evaluation import evaluate
from reddit_communities.lpa_engine import detect_communities, validate_partition
from reddit_communities.stability import adjusted_rand_index, compare_seeds


def named(graph):
    return nx.relabel_nodes(graph, {node: f"u{node:02d}" for node in graph})


@pytest.mark.parametrize(
    "graph",
    [
        nx.Graph(),
        nx.empty_graph(1),
        nx.empty_graph(4),
        nx.complete_graph(6),
        nx.path_graph(10),
        nx.cycle_graph(4),
        nx.star_graph(8),
        nx.barbell_graph(5, 0),
        nx.disjoint_union(nx.complete_graph(4), nx.path_graph(4)),
    ],
)
def test_known_graph_invariants(graph):
    graph = named(graph)
    first = detect_communities(graph, 42)
    second = detect_communities(graph, 42)
    assert first == second
    assert set(first) == set(graph)
    metrics = evaluate(graph, first, 0.1)
    assert sum(metrics.community_sizes) == len(graph)
    if graph.number_of_edges():
        assert math.isfinite(metrics.modularity)
    else:
        assert metrics.modularity is None
        assert metrics.intra_community_edge_fraction is None
    for isolate in nx.isolates(graph):
        assert list(first.values()).count(first[isolate]) == 1


@given(st.integers(min_value=0, max_value=40), st.integers(min_value=0, max_value=2**16))
@settings(max_examples=35, deadline=None)
def test_generated_graphs(nodes, seed):
    graph = named(nx.gnp_random_graph(nodes, 0.15, seed=seed))
    nx.set_edge_attributes(graph, 2.0, "weight")
    partition = detect_communities(graph, seed)
    assert set(partition) == set(graph)
    assert detect_communities(graph, seed) == partition
    assert sum(evaluate(graph, partition, 0).community_sizes) == nodes


def test_weighted_pairs_and_reordered_insertion():
    graph = nx.Graph()
    graph.add_weighted_edges_from([("a", "b", 10), ("c", "d", 10), ("b", "c", 0.01)])
    result = detect_communities(graph, 42)
    assert result["a"] == result["b"] != result["c"] == result["d"]
    reverse = nx.Graph()
    reverse.add_edges_from(reversed(list(graph.edges(data=True))))
    assert detect_communities(reverse, 42) == result


@pytest.mark.parametrize(
    "graph", [nx.DiGraph([("a", "b")]), nx.MultiGraph([("a", "b")]), nx.Graph([("a", "a")])]
)
def test_graph_shape_rejected(graph):
    with pytest.raises(AnalysisError):
        detect_communities(graph, 1)


@pytest.mark.parametrize("weight", [0, -1, float("nan"), float("inf"), "bad"])
def test_invalid_weights_rejected(weight):
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=weight)
    with pytest.raises(AnalysisError):
        detect_communities(graph, 1)


def test_independent_modularity():
    graph = nx.Graph()
    graph.add_weighted_edges_from([("a", "b", 3), ("c", "d", 3), ("b", "c", 1)])
    partition = {"a": "x", "b": "x", "c": "y", "d": "y"}
    # Per-group independent formula internal_weight/m - (degree_sum/(2m))².
    expected = 2 * (3 / 7 - (7 / 14) ** 2)
    metrics = evaluate(graph, partition, 0.2)
    assert metrics.modularity == pytest.approx(expected)
    assert metrics.intra_community_edge_fraction == pytest.approx(2 / 3)
    assert evaluate(graph, dict.fromkeys(graph, "one"), 0).modularity == pytest.approx(0)
    with pytest.raises(AnalysisError):
        validate_partition(graph, {"a": "x"})


def test_ari_known_and_degenerate_cases():
    a = {"a": "x", "b": "x", "c": "y", "d": "y"}
    b = {"a": "n", "b": "m", "c": "n", "d": "m"}
    assert adjusted_rand_index(a, b) == pytest.approx(-0.5)
    assert adjusted_rand_index(a, {node: "renamed_" + label for node, label in a.items()}) == 1
    assert adjusted_rand_index({}, {}) == 1
    assert adjusted_rand_index({"a": "one"}, {"a": "two"}) == 1
    assert adjusted_rand_index(dict.fromkeys(a, "all"), dict.fromkeys(a, "one")) == 1
    assert adjusted_rand_index({node: node for node in a}, {node: node for node in a}) == 1
    with pytest.raises(AnalysisError):
        adjusted_rand_index(a, {})
    graph = nx.Graph([("a", "b"), ("c", "d")])
    result = compare_seeds(graph, [1, 2, 3], True)
    assert len(result.comparisons) == 3 and result.mean_ari == 1
    assert compare_seeds(graph, [], True).mean_ari is None


def test_preview_bounds():
    graph = named(nx.complete_graph(450))
    partition = detect_communities(graph, 42)
    preview = graph_preview(graph, partition, 42, DEFAULT_LIMITS)
    assert len(preview.nodes) == 400 and len(preview.edges) == 1500
    assert preview.truncated
