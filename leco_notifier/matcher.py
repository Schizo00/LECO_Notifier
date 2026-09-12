from datetime import datetime


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def find_matches(subscriber: dict, outages: list, now: datetime) -> list:
    """Return outages in the subscriber's branch (and region, if given) whose
    street list mentions one of the subscriber's streets, and whose
    interruption window hasn't already passed.

    Matching is scoped to `subscriber["branch"]` because street names are not
    unique across LECO's 7 branch regions (e.g. more than one branch can have
    a "Main Street") — matching without that scope risks false positives.
    The same is true *within* a branch: each branch covers several towns
    (e.g. Galle branch covers GALLE, AMBALANGODA, HIKKADUWA), and a street
    name can repeat across them too. If `subscriber["region"]` is set, it's
    matched exactly (case-insensitive) against the outage's town, further
    narrowing the match; if unset, matching stays branch-wide as before.

    `now` must be a naive datetime in the same local time zone as LECO's
    published dates (Asia/Colombo) — see reminders.local_now()."""
    branch = (subscriber.get("branch") or "").strip().lower()
    region = (subscriber.get("region") or "").strip().lower()
    queries = [_normalize(s) for s in subscriber.get("streets", []) if s.strip()]
    if not branch or not queries:
        return []

    matches = []
    for outage in outages:
        if (outage.branch or "").strip().lower() != branch:
            continue
        if region and (outage.town or "").strip().lower() != region:
            continue
        if outage.date_to is not None and outage.date_to < now:
            continue
        haystack = _normalize(outage.streets_raw)
        if any(q in haystack for q in queries):
            matches.append(outage)
    return matches
