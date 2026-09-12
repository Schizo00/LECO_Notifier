import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SUBSCRIBERS_PATH = DATA_DIR / "subscribers.json"
STATE_PATH = DATA_DIR / "state.json"


def load_subscribers() -> list:
    if not SUBSCRIBERS_PATH.exists():
        return []
    with SUBSCRIBERS_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def save_subscribers(subscribers: list) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with SUBSCRIBERS_PATH.open("w", encoding="utf-8") as f:
        json.dump(subscribers, f, indent=2, ensure_ascii=False)
        f.write("\n")


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"sent": []}
    with STATE_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with STATE_PATH.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write("\n")
