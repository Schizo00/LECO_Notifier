from datetime import datetime
from types import SimpleNamespace

from leco_notifier.matcher import find_matches

NOW = datetime(2026, 9, 12, 8, 0, 0)


def _outage(streets_raw, date_to, branch="Galle", town="GALLE"):
    return SimpleNamespace(streets_raw=streets_raw, date_to=date_to, branch=branch, town=town)


def test_matches_case_insensitive_substring():
    sub = {"email": "a@example.com", "branch": "Galle", "streets": ["kandewatta rd"]}
    outages = [_outage("Kandewatta Rd(portion), Wackwella Rd", datetime(2026, 9, 20))]
    assert len(find_matches(sub, outages, now=NOW)) == 1


def test_no_match_for_unrelated_street():
    sub = {"email": "a@example.com", "branch": "Galle", "streets": ["Some Other Rd"]}
    outages = [_outage("Kandewatta Rd(portion)", datetime(2026, 9, 20))]
    assert find_matches(sub, outages, now=NOW) == []


def test_expired_outage_excluded():
    sub = {"email": "a@example.com", "branch": "Galle", "streets": ["Kandewatta Rd"]}
    outages = [_outage("Kandewatta Rd", datetime(2026, 9, 1))]  # already past
    assert find_matches(sub, outages, now=NOW) == []


def test_empty_streets_list_matches_nothing():
    sub = {"email": "a@example.com", "branch": "Galle", "streets": []}
    outages = [_outage("Kandewatta Rd", datetime(2026, 9, 20))]
    assert find_matches(sub, outages, now=NOW) == []


def test_missing_branch_matches_nothing():
    sub = {"email": "a@example.com", "streets": ["Kandewatta Rd"]}
    outages = [_outage("Kandewatta Rd", datetime(2026, 9, 20))]
    assert find_matches(sub, outages, now=NOW) == []


def test_same_street_name_in_different_branch_is_excluded():
    # Street names aren't unique across branches; a subscriber scoped to
    # Galle must not match an identically-named street in another branch.
    sub = {"email": "a@example.com", "branch": "Galle", "streets": ["Main Street"]}
    outages = [
        _outage("Main Street, and by roads", datetime(2026, 9, 20), branch="Kotte"),
        _outage("Main Street, and by roads", datetime(2026, 9, 20), branch="Galle"),
    ]
    matches = find_matches(sub, outages, now=NOW)
    assert len(matches) == 1
    assert matches[0].branch == "Galle"


def test_region_scopes_matching_within_a_branch():
    # A branch covers multiple towns (e.g. Galle branch covers GALLE and
    # AMBALANGODA), and street names can repeat across those too. A
    # subscriber with a region set must not match the same street name in a
    # different town within the same branch.
    sub = {"email": "a@example.com", "branch": "Galle", "region": "Ambalangoda", "streets": ["Galle Rd"]}
    outages = [
        _outage("Galle Rd, and by roads", datetime(2026, 9, 20), branch="Galle", town="GALLE"),
        _outage("Galle Rd, and by roads", datetime(2026, 9, 20), branch="Galle", town="AMBALANGODA"),
    ]
    matches = find_matches(sub, outages, now=NOW)
    assert len(matches) == 1
    assert matches[0].town == "AMBALANGODA"


def test_region_match_is_case_insensitive():
    sub = {"email": "a@example.com", "branch": "Galle", "region": "ambalangoda", "streets": ["Galle Rd"]}
    outages = [_outage("Galle Rd", datetime(2026, 9, 20), branch="Galle", town="AMBALANGODA")]
    assert len(find_matches(sub, outages, now=NOW)) == 1


def test_no_region_matches_across_all_towns_in_branch():
    # Without a region, matching stays branch-wide (backwards compatible).
    sub = {"email": "a@example.com", "branch": "Galle", "streets": ["Galle Rd"]}
    outages = [
        _outage("Galle Rd", datetime(2026, 9, 20), branch="Galle", town="GALLE"),
        _outage("Galle Rd", datetime(2026, 9, 20), branch="Galle", town="AMBALANGODA"),
    ]
    assert len(find_matches(sub, outages, now=NOW)) == 2
