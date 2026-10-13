from dataclasses import replace

import networkx as nx
import pytest

from reddit_communities.config import DEFAULT_LIMITS
from reddit_communities.errors import AnalysisError
from reddit_communities.graph_builder import build_graph
from reddit_communities.ingestion import ingest_csv
from reddit_communities.preprocessing import event_frame
from reddit_communities.schemas import AnalysisConfig


@pytest.mark.parametrize(
    "data,name,code",
    [
        (b"", "a.csv", "EMPTY_FILE"),
        (b"a", "a.txt", "FILE_TYPE"),
        (b"\xff", "a.csv", "ENCODING"),
        (b"a,a\n", "a.csv", "DUPLICATE_HEADERS"),
        (b"a\n", "a.csv", "MISSING_COLUMNS"),
        (b"a\x00", "a.csv", "MALFORMED_CSV"),
    ],
)
def test_fatal_inputs(data, name, code):
    with pytest.raises(AnalysisError) as caught:
        ingest_csv(data, name)
    assert caught.value.code == code


@pytest.mark.parametrize(
    "changes",
    [
        {"source_user": " "},
        {"target_user": ""},
        {"timestamp": "bad"},
        {"timestamp": "2026-01-01T00:00:00"},
        {"weight": "nan"},
        {"weight": "inf"},
        {"weight": "0"},
        {"weight": "-1"},
        {"weight": "oops"},
        {"interaction_type": "like"},
        {"source_user": "x" * 129},
        {"text": "x" * 16_385},
    ],
)
def test_quarantine_reconciles(make_csv, changes):
    dataset = ingest_csv(make_csv([{}, changes]), "a.csv")
    assert dataset.quality.input_rows == 2
    assert dataset.quality.accepted_rows == dataset.quality.rejected_rows == 1
    assert dataset.quality.rejections[0].row == 3


def test_dedup_before_aggregation_and_selfloops(make_csv):
    data = make_csv(
        [
            {"interaction_id": "e1", "weight": "2"},
            {"interaction_id": "e1", "weight": "2"},
            {"interaction_id": "e1", "weight": "3"},
            {"interaction_id": "e2", "source_user": "Bob", "target_user": "Alice"},
            {"source_user": "Alice", "target_user": "Alice"},
        ]
    )
    dataset = ingest_csv(data, "a.csv")
    assert dataset.quality.model_dump(exclude={"rejections"}) == dict(
        input_rows=5, accepted_rows=2, duplicate_rows=1, rejected_rows=1, self_loops=1
    )
    result = build_graph(dataset.events, AnalysisConfig())
    assert result.graph["Alice"]["Bob"]["weight"] == 3
    assert result.summary.edges == 1
    assert event_frame(dataset.events).iloc[1]["source_user"] == "Bob"


def test_fingerprint_utc_case_and_real_repeats(make_csv):
    dataset = ingest_csv(
        make_csv(
            [
                {"interaction_id": "", "source_user": " Alice "},
                {"interaction_id": "", "timestamp": "2026-01-01T05:30:00+05:30"},
                {"interaction_id": "", "timestamp": "2026-01-01T00:01:00Z"},
                {"source_user": "alice"},
            ]
        ),
        "a.csv",
    )
    assert dataset.quality.duplicate_rows == 1
    graph = build_graph(dataset.events, AnalysisConfig()).graph
    assert set(graph) == {"Alice", "alice", "Bob"}
    assert graph["Alice"]["Bob"]["weight"] == 2


def test_mapping_bom_and_ragged(sample_bytes):
    data = sample_bytes.replace(b"source_user", b"author", 1)
    assert ingest_csv(b"\xef\xbb\xbf" + data, "a.csv", {"author": "source_user"})
    with pytest.raises(AnalysisError, match="same field"):
        ingest_csv(sample_bytes, "a.csv", {"source_user": "target_user"})
    with pytest.raises(AnalysisError, match="same number"):
        ingest_csv(sample_bytes + b"ragged\n", "a.csv")
    with pytest.raises(AnalysisError, match="Malformed"):
        ingest_csv(sample_bytes + b'"unterminated', "a.csv")


def test_limits(make_csv, sample_bytes):
    for limits in (replace(DEFAULT_LIMITS, upload_bytes=2), replace(DEFAULT_LIMITS, rows=1)):
        with pytest.raises(AnalysisError) as caught:
            ingest_csv(sample_bytes, "a.csv", limits=limits)
        assert caught.value.status == 413
    with pytest.raises(AnalysisError, match="No usable"):
        ingest_csv(make_csv([{"weight": "NaN"}]), "a.csv")


def test_graph_filters_isolates_components(make_csv):
    dataset = ingest_csv(
        make_csv(
            [
                {"source_user": "a", "target_user": "b", "weight": "2"},
                {"source_user": "c", "target_user": "d", "weight": ".5"},
                {"source_user": "z", "target_user": "x", "weight": "3", "subreddit": "other"},
            ]
        ),
        "a.csv",
    )
    result = build_graph(dataset.events, AnalysisConfig(subreddits=["science"]))
    assert result.summary.nodes == 4 and result.summary.isolates == 2
    assert result.summary.threshold_removed_edges == result.summary.filtered_events == 1
    result = build_graph(dataset.events, AnalysisConfig(largest_component_only=True))
    assert set(result.graph) == {"a", "b"}
    assert result.summary.component_removed_nodes == 4
    result = build_graph(dataset.events, AnalysisConfig(weighted=False))
    assert all(data["weight"] == 1 for _, _, data in result.graph.edges(data=True))
    empty = build_graph(dataset.events, AnalysisConfig(interaction_types=["mention"]))
    assert not empty.graph and empty.summary.total_edge_weight == 0


def test_graph_deterministic_and_overflow(make_csv, sample_bytes):
    events = ingest_csv(sample_bytes, "a.csv").events
    first = build_graph(events, AnalysisConfig(minimum_weight=0.1))
    second = build_graph(tuple(reversed(events)), AnalysisConfig(minimum_weight=0.1))
    assert list(first.graph) == list(second.graph)
    assert list(first.graph.edges(data=True)) == list(second.graph.edges(data=True))
    assert first.summary == second.summary
    assert nx.number_connected_components(first.graph) == 1
    for rows in ([{"weight": "1e308"}, {"weight": "1e308"}], [{"weight": "1e308"}]):
        with pytest.raises(AnalysisError, match="numeric limits"):
            build_graph(ingest_csv(make_csv(rows), "a.csv").events, AnalysisConfig())
    with pytest.raises(AnalysisError, match="node budget"):
        build_graph(events, AnalysisConfig(), replace(DEFAULT_LIMITS, graph_nodes=1))


def test_time_window_inclusive(make_csv):
    dataset = ingest_csv(make_csv([{}, {"timestamp": "2026-01-02T00:00:00Z"}]), "a.csv")
    config = AnalysisConfig(start_time="2026-01-01T00:00:00Z", end_time="2026-01-01T00:00:00Z")
    assert build_graph(dataset.events, config).summary.selected_events == 1
