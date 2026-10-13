"""Killable subprocess isolation; deadlines bound the complete analytical pipeline."""

import multiprocessing as mp
import threading
import time
from multiprocessing.connection import Connection

from .analysis import analyze
from .config import DEFAULT_LIMITS, Limits
from .errors import AnalysisError
from .schemas import AnalysisConfig, AnalysisResult, ValidatedDataset


def worker_entry(
    sender: Connection,
    dataset: ValidatedDataset,
    config: AnalysisConfig,
    limits: Limits,
    run_id: str | None,
) -> None:
    try:
        result = analyze(dataset, config, limits, run_id)
        sender.send({"result": result.model_dump(mode="json")})
    except AnalysisError as error:
        sender.send({"error": error.payload(), "status": error.status})
    except Exception:
        # Process boundary recovery: do not disclose unexpected exception data to the caller.
        sender.send(
            {
                "error": {
                    "code": "ANALYSIS_FAILED",
                    "message": "Analysis failed safely",
                    "details": {},
                },
                "status": 500,
            }
        )
    finally:
        sender.close()


def run_with_timeout(
    dataset: ValidatedDataset,
    config: AnalysisConfig,
    timeout_seconds: float = 60,
    limits: Limits = DEFAULT_LIMITS,
    cancel: threading.Event | None = None,
    run_id: str | None = None,
) -> AnalysisResult:
    context = mp.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=worker_entry, args=(sender, dataset, config, limits, run_id))
    process.start()
    sender.close()
    deadline = time.monotonic() + timeout_seconds
    try:
        while True:
            if cancel is not None and cancel.is_set():
                raise AnalysisError("CANCELLED", "Analysis was cancelled", 409)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AnalysisError(
                    "TIMEOUT", "Analysis exceeded its configured runtime budget", 504
                )
            if receiver.poll(min(remaining, 0.05)):
                try:
                    payload = receiver.recv()
                except EOFError as error:
                    raise AnalysisError(
                        "WORKER_FAILED", "Analysis worker stopped unexpectedly", 500
                    ) from error
                if "error" in payload:
                    failure = payload["error"]
                    raise AnalysisError(
                        failure["code"], failure["message"], payload["status"], failure["details"]
                    )
                return AnalysisResult.model_validate(payload["result"])
            if not process.is_alive():
                raise AnalysisError("WORKER_FAILED", "Analysis worker stopped unexpectedly", 500)
    finally:
        receiver.close()
        if process.is_alive():
            process.terminate()
        process.join(timeout=2)
        if process.is_alive():
            process.kill()
            process.join(timeout=2)
        process.close()
