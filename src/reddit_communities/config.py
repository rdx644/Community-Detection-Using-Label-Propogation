"""Resource budgets, shared by ingestion, services and API."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Limits:
    upload_bytes: int = 5 * 1024 * 1024
    rows: int = 50_000
    graph_nodes: int = 10_000
    graph_edges: int = 50_000
    timeout_seconds: float = 60.0
    preview_nodes: int = 400
    preview_edges: int = 1_500
    retained_items: int = 20
    retention_seconds: float = 1_800.0
    concurrent_jobs: int = 2


DEFAULT_LIMITS = Limits()
