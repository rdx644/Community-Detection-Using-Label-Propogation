import csv
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from reddit_communities.schemas import REQUIRED_COLUMNS, AnalysisConfig, DataQuality

ROOT = Path(__file__).resolve().parents[2]


def test_sample_contract():
    with (ROOT / "data/sample/sample_interactions.csv").open(encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        assert set(REQUIRED_COLUMNS) <= set(reader.fieldnames or [])
        rows = list(reader)
    assert len(rows) == 267
    assert len({row["interaction_id"] for row in rows}) == len(rows)
    for row in rows:
        assert datetime.fromisoformat(row["timestamp"]).tzinfo
        assert float(row["weight"]) > 0
        assert row["source_user"] != row["target_user"]


@pytest.mark.parametrize(
    "options",
    [
        {"minimum_weight": 0},
        {"minimum_weight": float("inf")},
        {"seed": -1},
        {"start_time": "2026-01-01"},
        {"interaction_types": []},
        {"stability_seeds": [1, 1]},
        {"stability_seeds": [-1]},
        {"unknown": True},
        {"start_time": "2026-02-01T00:00:00Z", "end_time": "2026-01-01T00:00:00Z"},
    ],
)
def test_invalid_configuration(options):
    with pytest.raises(ValidationError):
        AnalysisConfig(**options)


def test_quality_counts_reconcile():
    assert DataQuality(
        input_rows=4, accepted_rows=1, duplicate_rows=1, rejected_rows=1, self_loops=1
    )
    with pytest.raises(ValidationError):
        DataQuality(input_rows=1)
