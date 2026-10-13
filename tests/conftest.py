import pytest
from cryptography.fernet import Fernet

TEST_KEY = Fernet.generate_key().decode()


@pytest.fixture(autouse=True)
def encryption_key(monkeypatch):
    """store.py now encrypts/decrypts everything it reads and writes, so
    every test needs a valid key in the environment regardless of whether
    it cares about encryption itself."""
    monkeypatch.setenv("LECO_ENCRYPTION_KEY", TEST_KEY)
