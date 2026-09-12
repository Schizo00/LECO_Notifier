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


def test_seven_day_stage_only_on_exact_day():
    assert STAGE_7_DAY in eligible_stages(_outage(7), TODAY)
    assert STAGE_7_DAY not in eligible_stages(_outage(6), TODAY)
    assert STAGE_7_DAY not in eligible_stages(_outage(8), TODAY)


def test_one_day_stage_only_on_exact_day():
    assert STAGE_1_DAY in eligible_stages(_outage(1), TODAY)
    assert STAGE_1_DAY not in eligible_stages(_outage(0), TODAY)
    assert STAGE_1_DAY not in eligible_stages(_outage(2), TODAY)


def test_no_date_from_only_yields_immediate():
    outage = SimpleNamespace(date_from=None)
    assert eligible_stages(outage, TODAY) == [STAGE_IMMEDIATE]


def test_local_now_honors_fake_now_override(monkeypatch):
    monkeypatch.setenv("LECO_FAKE_NOW", "2026-09-20T09:00:00")
    from leco_notifier.reminders import local_now

    now = local_now()
    assert (now.year, now.month, now.day) == (2026, 9, 20)
