import json

from leco_notifier import add_subscriber
from leco_notifier import store


def _run(monkeypatch, tmp_path, argv):
    subscribers_path = tmp_path / "subscribers.json"
    if not subscribers_path.exists():
        subscribers_path.write_text("[]")
    monkeypatch.setattr(store, "SUBSCRIBERS_PATH", subscribers_path)
    monkeypatch.setattr("sys.argv", ["leco-add-subscriber"] + argv)
    result = add_subscriber.main()
    return result, json.loads(subscribers_path.read_text())


def test_adds_subscriber_without_region(tmp_path, monkeypatch):
    result, subs = _run(monkeypatch, tmp_path, ["a@example.com", "Galle", "Kandewatta Rd"])
    assert result == 0
    assert subs == [{"email": "a@example.com", "branch": "Galle", "streets": ["Kandewatta Rd"]}]


def test_adds_subscriber_with_region(tmp_path, monkeypatch):
    result, subs = _run(
        monkeypatch, tmp_path, ["a@example.com", "Galle", "--region", "Ambalangoda", "Galle Rd"]
    )
    assert result == 0
    assert subs == [
        {"email": "a@example.com", "branch": "Galle", "region": "Ambalangoda", "streets": ["Galle Rd"]}
    ]


def test_unknown_branch_is_rejected(tmp_path, monkeypatch):
    result, subs = _run(monkeypatch, tmp_path, ["a@example.com", "Nowhereville", "Main St"])
    assert result != 0
    assert subs == []


def test_branch_name_is_case_insensitive_and_normalized(tmp_path, monkeypatch):
    result, subs = _run(monkeypatch, tmp_path, ["a@example.com", "galle", "Kandewatta Rd"])
    assert result == 0
    assert subs[0]["branch"] == "Galle"


def test_same_email_different_regions_stay_separate_entries(tmp_path, monkeypatch):
    _run(monkeypatch, tmp_path, ["a@example.com", "Galle", "--region", "Galle", "Kandewatta Rd"])
    result, subs = _run(
        monkeypatch, tmp_path, ["a@example.com", "Galle", "--region", "Ambalangoda", "Robert Soyza Mw"]
    )
    assert result == 0
    assert len(subs) == 2
    assert {s["region"] for s in subs} == {"Galle", "Ambalangoda"}


def test_same_email_branch_and_region_merges_streets(tmp_path, monkeypatch):
    _run(monkeypatch, tmp_path, ["a@example.com", "Galle", "--region", "Galle", "Kandewatta Rd"])
    result, subs = _run(
        monkeypatch, tmp_path, ["a@example.com", "Galle", "--region", "Galle", "Wackwella Rd"]
    )
    assert result == 0
    assert len(subs) == 1
    assert subs[0]["streets"] == ["Kandewatta Rd", "Wackwella Rd"]
