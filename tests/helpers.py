import json
from pathlib import Path

from leco_notifier.crypto import decrypt_bytes, encrypt_bytes


def write_encrypted_json(path: Path, data) -> None:
    path.write_bytes(encrypt_bytes(json.dumps(data).encode("utf-8")))


def read_encrypted_json(path: Path):
    return json.loads(decrypt_bytes(path.read_bytes()))
