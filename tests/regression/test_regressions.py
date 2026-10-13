import networkx as nx
import pytest

from reddit_communities.analysis import analyze
from reddit_communities.errors import AnalysisError
from reddit_communities.evaluation import evaluate
from reddit_communities.graph_builder import build_graph
from reddit_communities.ingestion import ingest_csv
from reddit_communities.provenance import pseudonym
from reddit_communities.schemas import AnalysisConfig


@pytest.mark.parametrize("scale", [1e-200, 1e150, 1])
def test_modularity_invariant_under_extreme_uniform_scaling(scale):
    graph = nx.Graph()
    graph.add_weighted_edges_from([("a", "b", 3 * scale), ("c", "d", 3 * scale), ("b", "c", scale)])
    memberships = {"a": "x", "b": "x", "c": "y", "d": "y"}
    assert evaluate(graph, memberships, 0).modularity == pytest.approx(2 * (3 / 7 - 0.25))


@pytest.mark.parametrize("weight", [1, 2, 3])
def test_largest_component_preview_and_analysis_choose_same_tied_component(make_csv, weight):
    pairs = [("a", "b"), ("a", "c"), ("x", "y"), ("x", "z"), ("y", "z")]
    dataset = ingest_csv(
        make_csv([{"source_user": a, "target_user": b, "weight": str(weight)} for a, b in pairs]),
        "tied.csv",
    )
    config = AnalysisConfig(largest_component_only=True)
    preview = build_graph(dataset.events, config)
    result = analyze(dataset, config)
    assert preview.summary == result.summary
    assert result.metrics.edges == 2
    assert set(result.memberships) == {
        pseudonym(node, dataset.fingerprint) for node in ("a", "b", "c")
    }


def test_bounded_headers():
    for data in (b",".join(str(index).encode() for index in range(101)), b"a" * 129):
        with pytest.raises(AnalysisError) as caught:
            ingest_csv(data, "headers.csv")
        assert caught.value.code == "HEADER_LIMIT"
