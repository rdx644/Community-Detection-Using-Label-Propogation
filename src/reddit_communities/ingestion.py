"""Bounded strict CSV parsing and reconciled quarantine reporting."""

import csv
import hashlib
import io

from .config import DEFAULT_LIMITS, Limits
from .errors import AnalysisError
from .preprocessing import event_fingerprint
from .schemas import (
    OPTIONAL_COLUMNS,
    REQUIRED_COLUMNS,
    DataQuality,
    Event,
    Rejection,
    ValidatedDataset,
)
from .validation import parse_event


def ingest_csv(
    data: bytes,
    filename: str,
    mapping: dict[str, str] | None = None,
    limits: Limits = DEFAULT_LIMITS,
) -> ValidatedDataset:
    if not filename.lower().endswith(".csv"):
        raise AnalysisError("FILE_TYPE", "Upload a .csv file", 400)
    if len(data) > limits.upload_bytes:
        raise AnalysisError("FILE_TOO_LARGE", "CSV exceeds the 5 MiB upload budget", 413)
    if not data:
        raise AnalysisError("EMPTY_FILE", "The CSV file is empty", 400)
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise AnalysisError("ENCODING", "Save the CSV as UTF-8 and upload again", 400) from error
    if "\x00" in text:
        raise AnalysisError("MALFORMED_CSV", "CSV must not contain null bytes", 400)
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        headers = [header.strip() for header in next(reader)]
    except (StopIteration, csv.Error) as error:
        raise AnalysisError("MALFORMED_CSV", "CSV needs a valid header row", 400) from error
    if len(headers) > 100 or any(len(header) > 128 for header in headers):
        raise AnalysisError(
            "HEADER_LIMIT", "Use at most 100 columns with headers of 128 characters", 413
        )
    if len(set(headers)) != len(headers) or any(not header for header in headers):
        raise AnalysisError("DUPLICATE_HEADERS", "Headers must be nonempty and unique", 400)
    mapping = mapping or {}
    if set(mapping) - set(headers) or set(mapping.values()) - set(
        REQUIRED_COLUMNS + OPTIONAL_COLUMNS
    ):
        raise AnalysisError(
            "INVALID_MAPPING", "Map existing headers to canonical schema fields", 400
        )
    canonical = [mapping.get(header, header) for header in headers]
    if len(set(canonical)) != len(canonical):
        raise AnalysisError("INVALID_MAPPING", "Two headers cannot map to the same field", 400)
    missing = sorted(set(REQUIRED_COLUMNS) - set(canonical))
    if missing:
        raise AnalysisError(
            "MISSING_COLUMNS",
            "Required columns are missing; supply a column mapping",
            422,
            {"missing_columns": missing, "available_columns": headers},
        )
    events: list[Event] = []
    by_id: dict[str, tuple[object, ...]] = {}
    fingerprints: set[tuple[object, ...]] = set()
    rejections: list[Rejection] = []
    counts = dict(input_rows=0, accepted_rows=0, rejected_rows=0, duplicate_rows=0, self_loops=0)
    try:
        for row_number, values in enumerate(reader, start=2):
            counts["input_rows"] += 1
            if counts["input_rows"] > limits.rows:
                raise AnalysisError("ROW_LIMIT", "CSV exceeds the supported row budget", 413)
            if len(values) != len(canonical):
                raise AnalysisError(
                    "MALFORMED_CSV",
                    "Each record must have the same number of fields as the header",
                    400,
                    {"row": row_number},
                )
            try:
                event = parse_event(dict(zip(canonical, values, strict=True)))
                fingerprint = event_fingerprint(event)
                if event.interaction_id:
                    previous = by_id.get(event.interaction_id)
                    if previous is not None and previous != fingerprint:
                        raise AnalysisError(
                            "DUPLICATE_ID_CONFLICT",
                            "An interaction ID refers to conflicting events",
                        )
                    duplicate = previous is not None
                    by_id[event.interaction_id] = fingerprint
                else:
                    duplicate = fingerprint in fingerprints
                    fingerprints.add(fingerprint)
                if duplicate:
                    counts["duplicate_rows"] += 1
                elif event.source_user == event.target_user:
                    counts["self_loops"] += 1
                else:
                    events.append(event)
                    counts["accepted_rows"] += 1
            except AnalysisError as error:
                counts["rejected_rows"] += 1
                if len(rejections) < 50:
                    rejections.append(
                        Rejection(row=row_number, code=error.code, message=error.message)
                    )
    except csv.Error as error:
        raise AnalysisError(
            "MALFORMED_CSV", "Malformed CSV quoting or oversized cell", 400
        ) from error
    quality = DataQuality(**counts, rejections=rejections)
    if not events:
        raise AnalysisError(
            "NO_USABLE_EVENTS",
            "No usable interactions remain after validation",
            422,
            {"quality": quality.model_dump()},
        )
    return ValidatedDataset(
        tuple(events),
        quality,
        hashlib.sha256(data).hexdigest(),
        tuple(canonical),
        tuple(sorted(mapping.items())),
    )
