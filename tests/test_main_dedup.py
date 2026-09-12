import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from leco_notifier import main as main_module
from leco_notifier import store

FIXTURE = Path(__file__).parent / "fixtures" / "area1.html"
LOCAL_TZ = ZoneInfo("Asia/Colombo")


def _setup_tmp_store(tmp_path, monkeypatch):
    subscribers_path = tmp_path / "subscribers.json"
    state_path = tmp_path / "state.json"
    subscribers_path.write_text(
        json.dumps([{"email": "a@example.com", "branch": "Galle", "streets": ["Kandewatta Rd"]}])
    )
    state_path.write_text(json.dumps({"sent": []}))
    monkeypatch.setattr(store, "SUBSCRIBERS_PATH", subscribers_path)
    monkeypatch.setattr(store, "STATE_PATH", state_path)
    return subscribers_path, state_path


def test_second_run_same_day_sends_nothing_new(tmp_path, monkeypatch):
    _setup_tmp_store(tmp_path, monkeypatch)
    monkeypatch.setattr(main_module, "fetch_all_areas", lambda: [(1, FIXTURE.read_text())])

    sent_calls = []
    monkeypatch.setattr(
        main_module, "send_email", lambda to, subject, body: sent_calls.append((to, subject))
    )

    main_module.main()
    assert len(sent_calls) == 1  # one consolidated email with the initial matches

    sent_calls.clear()
    main_module.main()
    assert sent_calls == []  # nothing new the second time the same day


def test_immediate_and_coinciding_reminder_collapse_into_one_stage(tmp_path, monkeypatch):
    """If an outage is first discovered exactly 1 (or 7) day(s) before it
    happens, `immediate` and the reminder stage both become due in the same
    run. That's one event, not two — a "reminder" implies a prior notice
    existed, which contradicts "immediate" meaning first contact. Only one
    entry should be emailed, but the coinciding stage must still be recorded
    as fulfilled so it doesn't fire separately later."""
    subscribers_path, state_path = _setup_tmp_store(tmp_path, monkeypatch)

    fixed_now = datetime(2026, 9, 10, 8, 0, 0, tzinfo=LOCAL_TZ)
    outage = SimpleNamespace(
        id="fixed-outage-id",
        branch="Galle",
        town="GALLE",
        source="LECO",
        section="Current Month",
        date_from=datetime(2026, 9, 11, 12, 0, 0),  # exactly 1 day after fixed_now
        date_to=datetime(2026, 9, 11, 16, 0, 0),
        date_from_raw="2026-09-11 12:00 PM",
        date_to_raw="2026-09-11 04:00 PM",
        streets=["Kandewatta Rd"],
        streets_raw="Kandewatta Rd and by roads",
    )

    monkeypatch.setattr(main_module, "fetch_all_areas", lambda: [])
    monkeypatch.setattr(main_module, "parse_all_areas", lambda pages: [outage])
    monkeypatch.setattr(main_module, "local_now", lambda: fixed_now)

    sent_calls = []
    monkeypatch.setattr(
        main_module, "send_email", lambda to, subject, body: sent_calls.append((to, subject, body))
    )

    main_module.main()

    assert len(sent_calls) == 1
    _, subject, body = sent_calls[0]
    assert "1 update" in subject
    assert body.count("Kandewatta Rd and by roads") == 1  # outage listed once, not twice
    assert "New notice" in body
    assert "tomorrow" not in body.lower()

    state = json.loads(state_path.read_text())
    assert f"{outage.id}:a@example.com:immediate" in state["sent"]
    assert f"{outage.id}:a@example.com:1_day_reminder" in state["sent"]  # fulfilled, not re-fireable


def test_no_subscribers_does_not_fetch(tmp_path, monkeypatch):
    subscribers_path = tmp_path / "subscribers.json"
    subscribers_path.write_text("[]")
    monkeypatch.setattr(store, "SUBSCRIBERS_PATH", subscribers_path)

    called = []
    monkeypatch.setattr(main_module, "fetch_all_areas", lambda: called.append(True))

    main_module.main()
    assert called == []
