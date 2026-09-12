from datetime import datetime


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def find_matches(subscriber: dict, outages: list, now: datetime) -> list:
    """Return outages whose street list mentions one of the subscriber's streets
    and whose interruption window hasn't already passed.

    `now` must be a naive datetime in the same local time zone as LECO's
    published dates (Asia/Colombo) — see reminders.local_now()."""
    queries = [_normalize(s) for s in subscriber.get("streets", []) if s.strip()]
    if not queries:
        return []

    matches = []
    for outage in outages:
        if outage.date_to is not None and outage.date_to < now:
            continue
        haystack = _normalize(outage.streets_raw)
        if any(q in haystack for q in queries):
            matches.append(outage)
    return matches
