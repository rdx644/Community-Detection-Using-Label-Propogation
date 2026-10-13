"""Observed subreddit context, separate from interaction-based clustering."""

from collections import Counter, defaultdict

from .schemas import Community, Event


def summarize_subreddits(events: tuple[Event, ...], memberships: dict[str, str]) -> list[Community]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for event in events:
        # One incidence per community per event, including cross-community interactions.
        labels = {
            memberships[user]
            for user in (event.source_user, event.target_user)
            if user in memberships
        }
        for label in labels:
            counts[label][event.subreddit or "unknown"] += 1
    sizes = Counter(memberships.values())
    return [
        Community(
            community_id=label,
            size=size,
            subreddits=dict(sorted(counts[label].items(), key=lambda item: (-item[1], item[0]))),
        )
        for label, size in sorted(sizes.items())
    ]
