"""Symmetric encryption for data at rest (subscribers.json, state.json).

Both files contain real emails — state.json's dedup keys embed them too
(e.g. "hash:someone@example.com:immediate") — so both are encrypted with the
same key rather than leaving either as plaintext in git history.

This is encryption at rest, not a security boundary against the process
itself: whatever runs the notifier must hold the key to decrypt and
re-encrypt on every run, so the key is exactly as sensitive as the SMTP
password already is. Losing the key makes the encrypted files unrecoverable
(subscribers would need to re-subscribe); leaking it is equivalent to
leaking the plaintext.
"""

import base64
import os

from cryptography.fernet import Fernet, InvalidToken

KEY_ENV_VAR = "LECO_ENCRYPTION_KEY"


class EncryptionKeyError(RuntimeError):
    pass


def _load_key() -> bytes:
    raw = os.environ.get(KEY_ENV_VAR)
    if not raw:
        raise EncryptionKeyError(
            f"{KEY_ENV_VAR} is not set. Generate one with:\n"
            '  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"\n'
            f"and set it in .env (local) and as a GitHub Actions secret (scheduled runs)."
        )
    try:
        # Validate it's actually a well-formed Fernet key (32 urlsafe-base64 bytes)
        # up front, so a malformed key fails loudly here rather than as a
        # confusing InvalidToken on the first decrypt attempt.
        base64.urlsafe_b64decode(raw)
    except Exception as exc:
        raise EncryptionKeyError(f"{KEY_ENV_VAR} is not a valid Fernet key: {exc}") from exc
    return raw.encode("utf-8")


def encrypt_bytes(data: bytes) -> bytes:
    return Fernet(_load_key()).encrypt(data)


def decrypt_bytes(token: bytes) -> bytes:
    try:
        return Fernet(_load_key()).decrypt(token)
    except InvalidToken as exc:
        raise EncryptionKeyError(
            f"Failed to decrypt with {KEY_ENV_VAR} — the key is wrong, or the file is corrupted."
        ) from exc
