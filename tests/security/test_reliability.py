import time
from dataclasses import replace

import pytest

from reddit_communities.config import DEFAULT_LIMITS
from reddit_communities.errors import AnalysisError
from reddit_communities.schemas import AnalysisConfig
from reddit_communities.service import AnalysisService


def test_retention_capacity_and_session_ownership(sample_bytes):
    service = AnalysisService(replace(DEFAULT_LIMITS, retained_items=1))
    identifier = str(service.upload(sample_bytes, "sample.csv", "owner")["dataset_id"])
    with pytest.raises(AnalysisError) as error:
        service.upload(sample_bytes, "sample.csv", "owner")
    assert error.value.status == 429
    with pytest.raises(AnalysisError) as error:
        service.get_dataset(identifier, "other")
    assert error.value.status == 404
    service.datasets[identifier].created -= 1801
    with pytest.raises(AnalysisError):
        service.get_dataset(identifier, "owner")
    assert not service.datasets
    service.close()


def test_failed_second_run_does_not_replace_success(sample_bytes):
    service = AnalysisService()
    try:
        identifier = str(service.upload(sample_bytes, "sample.csv", "owner")["dataset_id"])
        first = service.start(identifier, "owner", AnalysisConfig())
        deadline = time.monotonic() + 30
        while service.get_run(first.run_id, "owner").status in {"queued", "running"}:
            assert time.monotonic() < deadline
            time.sleep(0.05)
        successful = service.get_run(first.run_id, "owner")
        assert successful.result is not None
        service.limits = replace(service.limits, timeout_seconds=0.001)
        second = service.start(identifier, "owner", AnalysisConfig())
        while service.get_run(second.run_id, "owner").status in {"queued", "running"}:
            assert time.monotonic() < deadline
            time.sleep(0.05)
        assert service.get_run(second.run_id, "owner").status == "failed"
        assert service.get_run(first.run_id, "owner") == successful
        service.jobs[first.run_id].created -= 1801
        with pytest.raises(AnalysisError):
            service.get_run(first.run_id, "owner")
    finally:
        service.close()


def test_no_capacity_for_workers(sample_bytes):
    service = AnalysisService(replace(DEFAULT_LIMITS, concurrent_jobs=0))
    identifier = str(service.upload(sample_bytes, "sample.csv", "owner")["dataset_id"])
    with pytest.raises(AnalysisError) as error:
        service.start(identifier, "owner", AnalysisConfig())
    assert error.value.code == "BUSY"


def test_script_content_never_becomes_identity_or_text_output(make_csv):
    from reddit_communities.analysis import analyze
    from reddit_communities.ingestion import ingest_csv

    data = make_csv(
        [
            {
                "source_user": '=HYPERLINK("https://evil.example")',
                "text": "<script>alert('bad')</script>",
            }
        ]
    )
    result = analyze(ingest_csv(data, "safe.csv"), AnalysisConfig())
    assert "HYPERLINK" not in result.model_dump_json()
    assert "<script>" not in result.model_dump_json()
    assert len(result.memberships) == 2
