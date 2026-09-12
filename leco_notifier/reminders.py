import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

# LECO's published dates are already Sri Lanka local times; "today" for the
# 7-day / 1-day thresholds must also be computed in that timezone, since the
# GitHub Actions runner executes in UTC and would otherwise round day
# boundaries incorrectly near midnight Sri Lanka time.
LOCAL_TZ = ZoneInfo("Asia/Colombo")

STAGE_IMMEDIATE = "immediate"
STAGE_7_DAY = "7_day_reminder"
STAGE_1_DAY = "1_day_reminder"

STAGE_LABELS = {
    STAGE_IMMEDIATE: "New notice",
    STAGE_7_DAY: "Reminder — 7 days away",
    STAGE_1_DAY: "Reminder — tomorrow",
}

# Order in which stages should be considered/displayed.
STAGE_ORDER = [STAGE_IMMEDIATE, STAGE_7_DAY, STAGE_1_DAY]


def local_now() -> datetime:
    """Current time in Sri Lanka local time.

    Honors LECO_FAKE_NOW (an ISO datetime, e.g. "2026-09-20T09:00:00") when
    set, so a real end-to-end run can be pointed at a specific day — e.g. to
    force the 7-day or 1-day-before stage to fire against a real, currently
    published outage — without waiting for the calendar to line up."""
    fake = os.environ.get("LECO_FAKE_NOW")
    if fake:
        return datetime.fromisoformat(fake).replace(tzinfo=LOCAL_TZ)
    return datetime.now(LOCAL_TZ)


def eligible_stages(outage, today: date) -> list:
    """Which reminder stages are due for this outage as of `today` (a local
    date). `immediate` is always a candidate — dedup against already-sent
    state is what makes it fire only once, the first time an outage is seen."""
    stages = [STAGE_IMMEDIATE]
    if outage.date_from:
        days_until = (outage.date_from.date() - today).days
        if days_until == 7:
            stages.append(STAGE_7_DAY)
        if days_until == 1:
            stages.append(STAGE_1_DAY)
    return stages
