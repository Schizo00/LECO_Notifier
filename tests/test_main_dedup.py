import json
from pathlib import Path

from leco_notifier import main as main_module
from leco_notifier import store

FIXTURE = Path(__file__).parent / "fixtures" / "area1.html"


def _setup_tmp_store(tmp_path, monkeypatch):
    subscribers_path = tmp_path / "subscribers.json"
    state_path = tmp_path / "state.json"
    subscribers_path.write_text(
        json.dumps([{"email": "a@example.com", "streets": ["Kandewatta Rd"]}])
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


def test_no_subscribers_does_not_fetch(tmp_path, monkeypatch):
    subscribers_path = tmp_path / "subscribers.json"
    subscribers_path.write_text("[]")
    monkeypatch.setattr(store, "SUBSCRIBERS_PATH", subscribers_path)

    called = []
    monkeypatch.setattr(main_module, "fetch_all_areas", lambda: called.append(True))

    main_module.main()
    assert called == []
