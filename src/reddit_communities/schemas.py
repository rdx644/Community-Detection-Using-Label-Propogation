"""Frozen typed domain and HTTP data contracts (v1)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

InteractionType = Literal["reply", "mention", "shared_discussion"]
RunStatus = Literal[
    "queued", "running", "success", "completed_with_warnings", "failed", "cancelled"
]
REQUIRED_COLUMNS = ("source_user", "target_user", "interaction_type", "timestamp", "subreddit")
OPTIONAL_COLUMNS = ("interaction_id", "weight", "post_id", "text")


def default_interaction_types() -> list[InteractionType]:
    return ["reply", "mention", "shared_discussion"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class AnalysisConfig(StrictModel):
    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    weighted: bool = True
    minimum_weight: float = Field(default=1.0, gt=0, le=1e12)
    start_time: datetime | None = None
    end_time: datetime | None = None
    interaction_types: list[InteractionType] = Field(default_factory=default_interaction_types)
    subreddits: list[str] = Field(default_factory=list, max_length=100)
    largest_component_only: bool = False
    stability_seeds: list[int] = Field(default_factory=lambda: [42, 7, 21], max_length=5)

    @model_validator(mode="after")
    def validate_options(self) -> "AnalysisConfig":
        for value in (self.start_time, self.end_time):
            if value is not None and value.tzinfo is None:
                raise ValueError("Time filters require an explicit timezone")
        if self.start_time and self.end_time and self.start_time > self.end_time:
            raise ValueError("Start time must not follow end time")
        if not self.interaction_types or len(set(self.interaction_types)) != len(
            self.interaction_types
        ):
            raise ValueError("Select at least one distinct interaction type")
        if len(set(self.stability_seeds)) != len(self.stability_seeds) or any(
            seed < 0 or seed > 2**32 - 1 for seed in self.stability_seeds
        ):
            raise ValueError("Stability seeds must be distinct integers in [0, 2^32-1]")
        return self


class Rejection(StrictModel):
    row: int
    code: str
    message: str


class DataQuality(StrictModel):
    input_rows: int = 0
    accepted_rows: int = 0
    rejected_rows: int = 0
    duplicate_rows: int = 0
    self_loops: int = 0
    rejections: list[Rejection] = Field(default_factory=list)

    @model_validator(mode="after")
    def reconcile(self) -> "DataQuality":
        if self.input_rows != (
            self.accepted_rows + self.rejected_rows + self.duplicate_rows + self.self_loops
        ):
            raise ValueError("Data-quality counts must reconcile")
        return self


@dataclass(frozen=True)
class Event:
    source_user: str
    target_user: str
    interaction_type: str
    timestamp: datetime
    subreddit: str
    weight: float
    interaction_id: str = ""
    post_id: str = ""
    text: str = ""


@dataclass(frozen=True)
class ValidatedDataset:
    events: tuple[Event, ...]
    quality: DataQuality
    fingerprint: str
    columns: tuple[str, ...]
    mapping: tuple[tuple[str, str], ...] = ()


class GraphSummary(StrictModel):
    nodes: int
    edges: int
    isolates: int
    connected_components: int
    selected_events: int
    filtered_events: int
    threshold_removed_edges: int
    component_removed_nodes: int
    total_edge_weight: float


class Metrics(StrictModel):
    nodes: int
    edges: int
    communities: int
    modularity: float | None
    intra_community_edge_fraction: float | None
    minimum_community_size: int
    median_community_size: float
    maximum_community_size: int
    community_sizes: list[int]
    runtime_seconds: float


class SeedComparison(StrictModel):
    seed_a: int
    seed_b: int
    adjusted_rand_index: float


class StabilityResult(StrictModel):
    seeds: list[int]
    comparisons: list[SeedComparison]
    mean_ari: float | None


class Community(StrictModel):
    community_id: str
    size: int
    subreddits: dict[str, int]


class GraphNode(StrictModel):
    id: str
    community_id: str
    degree: int
    x: float
    y: float


class GraphEdge(StrictModel):
    source: str
    target: str
    weight: float


class GraphPreview(StrictModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    truncated: bool


class Provenance(StrictModel):
    dataset_sha256: str
    membership_sha256: str
    created_at: datetime
    python_version: str
    networkx_version: str
    application_version: str
    algorithm: str = "networkx.asyn_lpa_communities"
    identifier_policy: str = "dataset-scoped SHA-256 pseudonyms"
    input_columns: list[str]
    column_mapping: dict[str, str]
    preprocessing_policy: str = "trim IDs; UTC; event dedup; drop loops; sum pairs; keep isolates"


class AnalysisResult(StrictModel):
    schema_version: str = "1.0"
    run_id: str
    status: Literal["success", "completed_with_warnings"]
    config: AnalysisConfig
    quality: DataQuality
    summary: GraphSummary
    memberships: dict[str, str]
    communities: list[Community]
    metrics: Metrics
    stability: StabilityResult
    graph: GraphPreview
    provenance: Provenance
    warnings: list[str]


class RunRequest(StrictModel):
    dataset_id: str
    config: AnalysisConfig = Field(default_factory=AnalysisConfig)


class RunView(StrictModel):
    run_id: str
    status: RunStatus
    result: AnalysisResult | None = None
    error: dict[str, Any] | None = None


class DatasetView(StrictModel):
    dataset_id: str
    quality: DataQuality
    fingerprint: str
    columns: list[str]
    subreddits: list[str]
    interaction_types: list[str]
    start_time: datetime
    end_time: datetime
    retention_seconds: float
