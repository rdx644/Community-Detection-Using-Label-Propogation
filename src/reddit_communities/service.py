"""Session ownership, expiring bounded state, asynchronous analysis lifecycle."""

import threading
import time
import uuid
from dataclasses import dataclass, field

from .config import DEFAULT_LIMITS, Limits
from .errors import AnalysisError
from .graph_builder import build_graph
from .ingestion import ingest_csv
from .preprocessing import event_frame
from .schemas import AnalysisConfig, GraphSummary, RunView, ValidatedDataset
from .worker import run_with_timeout


@dataclass
class DatasetEntry:
    owner: str
    dataset: ValidatedDataset
    created: float


@dataclass
class JobEntry:
    owner: str
    dataset_id: str
    view: RunView
    created: float
    cancel: threading.Event = field(default_factory=threading.Event)
    thread: threading.Thread | None = None


class AnalysisService:
    def __init__(self, limits: Limits = DEFAULT_LIMITS) -> None:
        self.limits = limits
        self.datasets: dict[str, DatasetEntry] = {}
        self.jobs: dict[str, JobEntry] = {}
        self.lock = threading.RLock()

    def prune(self) -> None:
        with self.lock:
            cutoff = time.monotonic() - self.limits.retention_seconds
            for identifier in list(self.datasets):
                if self.datasets[identifier].created < cutoff:
                    del self.datasets[identifier]
            for identifier in list(self.jobs):
                job = self.jobs[identifier]
                if job.created < cutoff and job.view.status not in {"queued", "running"}:
                    del self.jobs[identifier]

    def upload(
        self, data: bytes, filename: str, owner: str, mapping: dict[str, str] | None = None
    ) -> dict[str, object]:
        dataset = ingest_csv(data, filename, mapping, self.limits)
        with self.lock:
            self.prune()
            if len(self.datasets) >= self.limits.retained_items:
                raise AnalysisError(
                    "CAPACITY", "Dataset capacity reached; delete an earlier upload", 429
                )
            identifier = str(uuid.uuid4())
            self.datasets[identifier] = DatasetEntry(owner, dataset, time.monotonic())
        frame = event_frame(dataset.events)
        return {
            "dataset_id": identifier,
            "quality": dataset.quality.model_dump(),
            "fingerprint": dataset.fingerprint,
            "columns": list(dataset.columns),
            "subreddits": sorted(set(frame["subreddit"]) - {""}),
            "interaction_types": sorted(set(frame["interaction_type"])),
            "start_time": frame["timestamp"].min().isoformat(),
            "end_time": frame["timestamp"].max().isoformat(),
            "retention_seconds": self.limits.retention_seconds,
        }

    def get_dataset(self, identifier: str, owner: str) -> ValidatedDataset:
        with self.lock:
            self.prune()
            entry = self.datasets.get(identifier)
            if entry is None or entry.owner != owner:
                raise AnalysisError(
                    "NOT_FOUND", "Dataset is unavailable or expired; upload it again", 404
                )
            return entry.dataset

    def preview(self, identifier: str, owner: str, config: AnalysisConfig) -> GraphSummary:
        return build_graph(self.get_dataset(identifier, owner).events, config, self.limits).summary

    def start(self, identifier: str, owner: str, config: AnalysisConfig) -> RunView:
        dataset = self.get_dataset(identifier, owner)
        with self.lock:
            self.prune()
            active = sum(
                job.thread is not None and job.thread.is_alive() for job in self.jobs.values()
            )
            if active >= self.limits.concurrent_jobs:
                raise AnalysisError(
                    "BUSY", "Analysis capacity reached; wait for an active run", 429
                )
            if len(self.jobs) >= self.limits.retained_items:
                raise AnalysisError("CAPACITY", "Run capacity reached; delete an earlier run", 429)
            run_id = str(uuid.uuid4())
            job = JobEntry(
                owner, identifier, RunView(run_id=run_id, status="queued"), time.monotonic()
            )
            self.jobs[run_id] = job
            job.thread = threading.Thread(
                target=self._execute, args=(job, dataset, config), daemon=True
            )
            job.thread.start()
            return job.view.model_copy(deep=True)

    def _execute(self, job: JobEntry, dataset: ValidatedDataset, config: AnalysisConfig) -> None:
        with self.lock:
            if job.cancel.is_set():
                return
            job.view.status = "running"
        try:
            result = run_with_timeout(
                dataset,
                config,
                self.limits.timeout_seconds,
                self.limits,
                job.cancel,
                job.view.run_id,
            )
            with self.lock:
                if not job.cancel.is_set():
                    job.view = RunView(run_id=result.run_id, status=result.status, result=result)
        except AnalysisError as error:
            with self.lock:
                job.view.status = "cancelled" if job.cancel.is_set() else "failed"
                job.view.error = error.payload()
        except Exception:
            # Background task recovery boundary. Preserve all other successful job artifacts.
            with self.lock:
                job.view.status = "failed"
                job.view.error = {
                    "code": "JOB_FAILED",
                    "message": "Analysis could not complete",
                    "details": {},
                }

    def get_run(self, identifier: str, owner: str) -> RunView:
        with self.lock:
            self.prune()
            job = self.jobs.get(identifier)
            if job is None or job.owner != owner:
                raise AnalysisError("NOT_FOUND", "Run is unavailable or expired", 404)
            return job.view.model_copy(deep=True)

    def delete_run(self, identifier: str, owner: str) -> None:
        with self.lock:
            self.get_run(identifier, owner)
            job = self.jobs[identifier]
            if job.thread is not None and job.thread.is_alive():
                job.cancel.set()
                job.view.status = "cancelled"
            else:
                del self.jobs[identifier]

    def delete_dataset(self, identifier: str, owner: str) -> None:
        with self.lock:
            self.get_dataset(identifier, owner)
            for job in self.jobs.values():
                if job.dataset_id == identifier and job.view.status in {"queued", "running"}:
                    job.cancel.set()
                    job.view.status = "cancelled"
            del self.datasets[identifier]

    def close(self) -> None:
        for job in list(self.jobs.values()):
            job.cancel.set()
            if job.thread is not None:
                job.thread.join(timeout=5)
        self.datasets.clear()
        self.jobs.clear()
