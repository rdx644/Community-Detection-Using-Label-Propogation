"""Measured deterministic synthetic benchmark, never inferred performance claims."""

import csv
import io
import json
import os
import platform
import random
import subprocess
import time
import tracemalloc
from datetime import UTC, datetime, timedelta
from pathlib import Path

from reddit_communities.analysis import analyze
from reddit_communities.exports import atomic_write, export_memberships, export_report
from reddit_communities.ingestion import ingest_csv
from reddit_communities.schemas import AnalysisConfig

ROOT = Path(__file__).resolve().parents[1]


def benchmark_data(rows: int = 10_000) -> bytes:
    rng = random.Random(2026)
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(
        [
            "source_user",
            "target_user",
            "interaction_type",
            "timestamp",
            "subreddit",
            "interaction_id",
            "weight",
        ]
    )
    start = datetime(2026, 1, 1, tzinfo=UTC)
    for index in range(rows):
        group = index % 10
        first, second = rng.sample(range(100), 2)
        writer.writerow(
            [
                f"synthetic_{group}_{first}",
                f"synthetic_{group}_{second}",
                "reply",
                (start + timedelta(seconds=index)).isoformat(),
                f"synthetic_topic_{group}",
                f"benchmark_event_{index}",
                rng.randint(1, 5),
            ]
        )
    return stream.getvalue().encode()


if __name__ == "__main__":
    config = AnalysisConfig(minimum_weight=0.1)
    sample = ingest_csv((ROOT / "data/sample/sample_interactions.csv").read_bytes(), "sample.csv")
    demo = analyze(sample, config)
    atomic_write(ROOT / "artifacts/sample/result.json", demo.model_dump_json(indent=2).encode())
    atomic_write(ROOT / "artifacts/sample/memberships.csv", export_memberships(demo))
    atomic_write(ROOT / "artifacts/sample/report.md", export_report(demo).encode())
    atomic_write(
        ROOT / "artifacts/sample/data_quality_report.json",
        demo.quality.model_dump_json(indent=2).encode(),
    )
    data = benchmark_data()
    tracemalloc.start()
    started = time.perf_counter()
    dataset = ingest_csv(data, "benchmark.csv")
    result = analyze(dataset, config)
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    repeated = analyze(dataset, config)
    assert repeated.memberships == result.memberships
    assert sum(result.metrics.community_sizes) == result.metrics.nodes
    assert elapsed < 60, "Declared 60-second benchmark budget exceeded"
    cpu = platform.processor()
    if os.name == "nt":
        cpu = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).Name"],
            text=True,
        ).strip()
    evidence = {
        "recorded_at": datetime.now(UTC).isoformat(),
        "synthetic": True,
        "environment": {
            "os": platform.platform(),
            "python": platform.python_version(),
            "cpu": cpu,
            "logical_cpus": os.cpu_count(),
            "networkx": result.provenance.networkx_version,
        },
        "dataset": {
            "input_rows": dataset.quality.input_rows,
            "bytes": len(data),
            "sha256": dataset.fingerprint,
            "generator_seed": 2026,
        },
        "metrics": result.metrics.model_dump(),
        "total_wall_seconds": elapsed,
        "peak_python_allocated_mib": peak / 1024**2,
        "memory_note": "tracemalloc Python allocations; not process RSS or native NumPy memory",
        "target_seconds": 60,
        "passed": True,
        "membership_repeatable": True,
        "sample_metrics": demo.metrics.model_dump(),
        "configuration": config.model_dump(mode="json"),
    }
    atomic_write(
        ROOT / "artifacts/verification/benchmark.json",
        (json.dumps(evidence, indent=2) + "\n").encode(),
    )
    print(json.dumps(evidence, indent=2))
