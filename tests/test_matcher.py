from datetime import datetime
from types import SimpleNamespace

from leco_notifier.matcher import find_matches

NOW = datetime(2026, 9, 12, 8, 0, 0)


def _outage(streets_raw, date_to):
    return SimpleNamespace(streets_raw=streets_raw, date_to=date_to)


def test_matches_case_insensitive_substring():
    sub = {"email": "a@example.com", "streets": ["kandewatta rd"]}
    outages = [_outage("Kandewatta Rd(portion), Wackwella Rd", datetime(2026, 9, 20))]
    assert len(find_matches(sub, outages, now=NOW)) == 1


def test_no_match_for_unrelated_street():
    sub = {"email": "a@example.com", "streets": ["Some Other Rd"]}
    outages = [_outage("Kandewatta Rd(portion)", datetime(2026, 9, 20))]
    assert find_matches(sub, outages, now=NOW) == []


def test_expired_outage_excluded():
    sub = {"email": "a@example.com", "streets": ["Kandewatta Rd"]}
    outages = [_outage("Kandewatta Rd", datetime(2026, 9, 1))]  # already past
    assert find_matches(sub, outages, now=NOW) == []


def test_empty_streets_list_matches_nothing():
    sub = {"email": "a@example.com", "streets": []}
    outages = [_outage("Kandewatta Rd", datetime(2026, 9, 20))]
    assert find_matches(sub, outages, now=NOW) == []
