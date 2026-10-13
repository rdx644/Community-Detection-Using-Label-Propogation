"""Per-record validation, independent of ingestion transport and dashboard."""

import math
import re
from datetime import UTC, datetime

from .errors import AnalysisError
from .schemas import Event


def parse_event(row: dict[str, str]) -> Event:
    source = row["source_user"].strip()
    target = row["target_user"].strip()
    if not source or not target:
        raise AnalysisError("MISSING_USER", "Source and target identifiers are required")
    if any(len(value) > 128 or any(ord(c) < 32 for c in value) for value in (source, target)):
        raise AnalysisError("INVALID_USER", "Identifiers must be at most 128 printable characters")
    kind = row["interaction_type"].strip().lower()
    if kind not in {"reply", "mention", "shared_discussion"}:
        raise AnalysisError("INVALID_TYPE", "Use reply, mention or shared_discussion")
    timestamp = row["timestamp"].strip()
    try:
        if not re.match(r"^\d{4}-\d{2}-\d{2}T", timestamp):
            raise ValueError
        moment = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if moment.tzinfo is None or moment.utcoffset() is None:
            raise ValueError
        moment = moment.astimezone(UTC)
    except (ValueError, OverflowError) as error:
        raise AnalysisError(
            "INVALID_TIMESTAMP",
            "Use an ISO-8601 timestamp with timezone, e.g. 2026-01-01T12:00:00Z",
        ) from error
    try:
        weight = float(row.get("weight", "").strip() or "1")
    except ValueError as error:
        raise AnalysisError("INVALID_WEIGHT", "Weight must be a finite positive number") from error
    if not math.isfinite(weight) or weight <= 0:
        raise AnalysisError("INVALID_WEIGHT", "Weight must be a finite positive number")
    subreddit = row["subreddit"].strip()
    event_id = row.get("interaction_id", "").strip()
    post_id = row.get("post_id", "").strip()
    text = row.get("text", "")
    if any(len(value) > 128 for value in (subreddit, event_id, post_id)) or len(text) > 16_384:
        raise AnalysisError("FIELD_LIMIT", "Metadata fields exceed their supported length")
    return Event(source, target, kind, moment, subreddit, weight, event_id, post_id, text)
