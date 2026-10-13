import pytest
from cryptography.fernet import Fernet

from leco_notifier.crypto import EncryptionKeyError, decrypt_bytes, encrypt_bytes


def test_round_trip():
    data = b'{"sent": ["a:b:c"]}'
    assert decrypt_bytes(encrypt_bytes(data)) == data


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("LECO_ENCRYPTION_KEY", raising=False)
    with pytest.raises(EncryptionKeyError):
        encrypt_bytes(b"data")


def test_malformed_key_raises(monkeypatch):
    monkeypatch.setenv("LECO_ENCRYPTION_KEY", "not-a-valid-key")
    with pytest.raises(EncryptionKeyError):
        encrypt_bytes(b"data")


def test_wrong_key_fails_to_decrypt(monkeypatch):
    monkeypatch.setenv("LECO_ENCRYPTION_KEY", Fernet.generate_key().decode())
    token = encrypt_bytes(b"secret data")

    monkeypatch.setenv("LECO_ENCRYPTION_KEY", Fernet.generate_key().decode())
    with pytest.raises(EncryptionKeyError):
        decrypt_bytes(token)
