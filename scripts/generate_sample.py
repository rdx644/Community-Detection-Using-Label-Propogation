"""Deterministic synthetic interaction fixture. No real Reddit identifiers."""

import csv
from datetime import UTC, datetime, timedelta
from itertools import combinations
from pathlib import Path


def generate(destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "source_user",
        "target_user",
        "interaction_type",
        "timestamp",
        "subreddit",
        "interaction_id",
        "weight",
        "post_id",
        "text",
    ]
    rows = []
    topics = ["MachineLearning", "datascience", "cybersecurity", "learnprogramming"]
    moment = datetime(2026, 1, 1, tzinfo=UTC)
    for group, topic in enumerate(topics):
        users = [f"synthetic_{group + 1}_{i:02d}" for i in range(1, 13)]
        for a, b in combinations(users, 2):
            index = len(rows)
            rows.append(
                [
                    a,
                    b,
                    "reply" if index % 3 else "mention",
                    (moment + timedelta(minutes=index)).isoformat(),
                    topic,
                    f"event_{index:04d}",
                    3 + index % 5,
                    f"synthetic_post_{group}",
                    "",
                ]
            )
    for group in range(3):
        index = len(rows)
        rows.append(
            [
                f"synthetic_{group + 1}_01",
                f"synthetic_{group + 2}_01",
                "reply",
                (moment + timedelta(minutes=index)).isoformat(),
                topics[group],
                f"event_{index:04d}",
                0.2,
                "synthetic_bridge",
                "",
            ]
        )
    with destination.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        writer.writerows(rows)


if __name__ == "__main__":
    generate(Path(__file__).resolve().parents[1] / "data/sample/sample_interactions.csv")
