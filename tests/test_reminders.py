from datetime import date, datetime, timedelta
from types import SimpleNamespace

from leco_notifier.reminders import (
    STAGE_1_DAY,
    STAGE_7_DAY,
    STAGE_IMMEDIATE,
    eligible_stages,
)

TODAY = date(2026, 9, 12)


def _outage(days_from_today):
    dt = datetime.combine(TODAY + timedelta(days=days_from_today), datetime.min.time())
    return SimpleNamespace(date_from=dt)


def test_immediate_always_eligible_regardless_of_distance():
    for offset in [0, 1, 7, 30]:
        assert STAGE_IMMEDIATE in eligible_stages(_outage(offset), TODAY)


def test_seven_day_stage_eligible_anywhere_in_its_window():
    # Uses a window (2-7 days out), not an exact-day match, so a run missed
    # on the exact 7th day (site down, network error) still catches it on
    # day 6, 5, etc. — dedup against already-sent state is what stops it
    # firing more than once.
    for offset in [2, 3, 6, 7]:
        assert STAGE_7_DAY in eligible_stages(_outage(offset), TODAY)
    assert STAGE_7_DAY not in eligible_stages(_outage(8), TODAY)
    assert STAGE_7_DAY not in eligible_stages(_outage(1), TODAY)  # 1-day's window, not 7-day's
    assert STAGE_7_DAY not in eligible_stages(_outage(-1), TODAY)  # already started


def test_one_day_stage_eligible_anywhere_in_its_window():
    for offset in [0, 1]:
        assert STAGE_1_DAY in eligible_stages(_outage(offset), TODAY)
    assert STAGE_1_DAY not in eligible_stages(_outage(2), TODAY)
    assert STAGE_1_DAY not in eligible_stages(_outage(-1), TODAY)  # already started


def test_seven_day_and_one_day_windows_never_overlap():
    # If a run is missed entirely for days 7 down through 2 (e.g. the
    # scraper was down all week) and the next successful run lands on day 1,
    # the 7-day stage should never have become eligible at all — it's simply
    # missed, not fired late with stale "7 days away" wording.
    for offset in [0, 1]:
        stages = eligible_stages(_outage(offset), TODAY)
        assert STAGE_1_DAY in stages
        assert STAGE_7_DAY not in stages


def test_no_date_from_only_yields_immediate():
    outage = SimpleNamespace(date_from=None)
    assert eligible_stages(outage, TODAY) == [STAGE_IMMEDIATE]


def test_local_now_honors_fake_now_override(monkeypatch):
    monkeypatch.setenv("LECO_FAKE_NOW", "2026-09-20T09:00:00")
    from leco_notifier.reminders import local_now

    now = local_now()
    assert (now.year, now.month, now.day) == (2026, 9, 20)
