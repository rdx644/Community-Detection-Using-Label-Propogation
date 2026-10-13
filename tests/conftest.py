import csv
import io
from pathlib import Path

import pytest

from reddit_communities.schemas import OPTIONAL_COLUMNS, REQUIRED_COLUMNS


@pytest.fixture
def sample_bytes():
    return (
        Path(__file__).resolve().parents[1] / "data/sample/sample_interactions.csv"
    ).read_bytes()


@pytest.fixture
def make_csv():
    def create(rows, headers=REQUIRED_COLUMNS + OPTIONAL_COLUMNS):
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        for index, overrides in enumerate(rows):
            row = {
                "source_user": "Alice",
                "target_user": "Bob",
                "interaction_type": "reply",
                "timestamp": "2026-01-01T00:00:00Z",
                "subreddit": "science",
                "interaction_id": f"e{index}",
                "weight": "1",
                "post_id": "",
                "text": "",
            }
            row.update(overrides)
            writer.writerow({key: row[key] for key in headers})
        return stream.getvalue().encode()

    return create
