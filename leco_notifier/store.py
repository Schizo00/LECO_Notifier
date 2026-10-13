import json
from pathlib import Path

from .crypto import decrypt_bytes, encrypt_bytes

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SUBSCRIBERS_PATH = DATA_DIR / "subscribers.json.enc"
STATE_PATH = DATA_DIR / "state.json.enc"


def _load_encrypted_json(path: Path, default):
    if not path.exists():
        return default
    ciphertext = path.read_bytes()
    return json.loads(decrypt_bytes(ciphertext))


def _save_encrypted_json(path: Path, data) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    plaintext = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    path.write_bytes(encrypt_bytes(plaintext))


def load_subscribers() -> list:
    return _load_encrypted_json(SUBSCRIBERS_PATH, [])


def save_subscribers(subscribers: list) -> None:
    _save_encrypted_json(SUBSCRIBERS_PATH, subscribers)


def load_state() -> dict:
    return _load_encrypted_json(STATE_PATH, {"sent": []})


def save_state(state: dict) -> None:
    _save_encrypted_json(STATE_PATH, state)
