"""Canonical fingerprints and normalized event tables."""

from typing import Any

import pandas as pd

from .schemas import Event


def event_fingerprint(event: Event) -> tuple[Any, ...]:
    return (
        event.source_user,
        event.target_user,
        event.interaction_type,
        event.timestamp,
        event.subreddit,
        event.weight,
        event.post_id,
        event.text,
    )


def event_frame(events: tuple[Event, ...]) -> pd.DataFrame:
    """Internal directional table. Never returned directly by the public API."""
    return pd.DataFrame.from_records(
        [
            {
                "source_user": event.source_user,
                "target_user": event.target_user,
                "interaction_type": event.interaction_type,
                "timestamp": event.timestamp,
                "subreddit": event.subreddit,
                "weight": event.weight,
                "interaction_id": event.interaction_id,
                "post_id": event.post_id,
            }
            for event in events
        ]
    )
