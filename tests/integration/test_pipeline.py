import csv
import hashlib
import io
import json
import threading

import pytest

from reddit_communities.analysis import analyze
from reddit_communities.errors import AnalysisError
from reddit_communities.exports import atomic_write, export_memberships, export_report, safe_cell
from reddit_communities.ingestion import ingest_csv
from reddit_communities.schemas import AnalysisConfig, AnalysisResult
from reddit_communities.worker import run_with_timeout


def test_sample_pipeline_and_export_roundtrip(sample_bytes, tmp_path):
    dataset = ingest_csv(sample_bytes, "sample.csv")
    config = AnalysisConfig(minimum_weight=0.1)
    first = analyze(dataset, config)
    second = analyze(dataset, config)
    assert first.memberships == second.memberships
    assert first.provenance.membership_sha256 == second.provenance.membership_sha256
    assert first.metrics.nodes == 48 and first.metrics.edges == 267
    assert first.metrics.communities == 4
    assert first.metrics.community_sizes == [12, 12, 12, 12]
    assert first.stability.mean_ari == 1
    assert first.provenance.dataset_sha256 == hashlib.sha256(sample_bytes).hexdigest()
    assert "synthetic_" not in first.model_dump_json()
    rows = list(csv.DictReader(io.StringIO(export_memberships(first).decode())))
    assert {row["user_id"]: row["community_id"] for row in rows} == first.memberships
    assert all(row["run_id"] == first.run_id for row in rows)
    reloaded = AnalysisResult.model_validate(json.loads(first.model_dump_json()))
    assert reloaded == first
    assert first.run_id in export_report(first)
    destination = tmp_path / "export/result.json"
    atomic_write(destination, first.model_dump_json().encode())
    assert AnalysisResult.model_validate_json(destination.read_bytes()) == first
    atomic_write(destination, second.model_dump_json().encode())
    assert AnalysisResult.model_validate_json(destination.read_bytes()) == second


def test_empty_filters_and_warnings(make_csv):
    dataset = ingest_csv(make_csv([{}, {"weight": "NaN"}, {"target_user": "Alice"}]), "a.csv")
    result = analyze(dataset, AnalysisConfig(interaction_types=["mention"]))
    assert result.metrics.nodes == 0 and result.status == "completed_with_warnings"
    assert result.metrics.modularity is None
    assert result.graph.nodes == [] and result.memberships == {}
    assert len(result.warnings) == 3


def test_real_process_success_timeout_and_cancel(sample_bytes):
    dataset = ingest_csv(sample_bytes, "sample.csv")
    result = run_with_timeout(dataset, AnalysisConfig(), timeout_seconds=30)
    assert result.metrics.nodes == 48
    with pytest.raises(AnalysisError) as caught:
        run_with_timeout(dataset, AnalysisConfig(), timeout_seconds=0.001)
    assert caught.value.code == "TIMEOUT"
    cancelled = threading.Event()
    cancelled.set()
    with pytest.raises(AnalysisError) as caught:
        run_with_timeout(dataset, AnalysisConfig(), cancel=cancelled)
    assert caught.value.code == "CANCELLED"


@pytest.mark.parametrize("value", ["=SUM(A1)", "+1", "-1", "@formula", "\tformula", "\rformula"])
def test_spreadsheet_injection(value):
    assert safe_cell(value) == "'" + value


def test_atomic_export_failure_preserves_destination(tmp_path, monkeypatch):
    destination = tmp_path / "saved.csv"
    destination.write_bytes(b"successful")

    def fail(*args):
        raise OSError("destination unavailable")

    monkeypatch.setattr("reddit_communities.exports.os.replace", fail)
    with pytest.raises(OSError):
        atomic_write(destination, b"new")
    assert destination.read_bytes() == b"successful"
    assert list(tmp_path.iterdir()) == [destination]
