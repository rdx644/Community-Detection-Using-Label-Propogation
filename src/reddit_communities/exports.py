"""Portable exports from immutable successful results."""

import csv
import io
import json
import os
import tempfile
from pathlib import Path

from .schemas import AnalysisResult


def safe_cell(value: str) -> str:
    return "'" + value if value.startswith(("=", "+", "-", "@", "\t", "\r")) else value


def export_memberships(result: AnalysisResult) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(["run_id", "user_id", "community_id"])
    for node, label in sorted(result.memberships.items()):
        writer.writerow([safe_cell(result.run_id), safe_cell(node), safe_cell(label)])
    return stream.getvalue().encode("utf-8")


def export_report(result: AnalysisResult) -> str:
    metrics = result.metrics
    modularity = (
        "undefined (no edges)" if metrics.modularity is None else f"{metrics.modularity:.6f}"
    )
    return (
        "# Interaction community analysis\n\n"
        f"Run: `{result.run_id}`\n\n"
        f"Status: {result.status}\n\n"
        f"Nodes: {metrics.nodes}; edges: {metrics.edges}; communities: {metrics.communities}.\n\n"
        f"Weighted modularity: {modularity}. Runtime: {metrics.runtime_seconds:.6f} seconds.\n\n"
        "These are interaction communities, not verified academic interests or expertise.\n"
        "Subreddit context is interpreted separately from label propagation.\n\n"
        "## Reproducibility\n\n```json\n"
        + json.dumps(
            {
                "configuration": result.config.model_dump(mode="json"),
                "provenance": result.provenance.model_dump(mode="json"),
                "quality": result.quality.model_dump(),
            },
            indent=2,
        )
        + "\n```\n\nWarnings: "
        + ("; ".join(result.warnings) or "none")
        + "\n"
    )


def atomic_write(destination: Path, content: bytes) -> None:
    """Only publish completed exports; leave previous destination intact on failure."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".export-", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
