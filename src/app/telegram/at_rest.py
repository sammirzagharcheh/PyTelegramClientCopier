"""Optional Fernet sealing for bot tokens and bot StringSession blobs."""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

SEAL_PREFIX = "enc:v1:"


class CredentialSealError(ValueError):
    """Stored secret cannot be revealed (missing/wrong CREDENTIALS_AT_REST_KEY)."""


def _fernet() -> Fernet | None:
    key = (settings.credentials_at_rest_key or "").strip()
    if not key:
        return None
    try:
        return Fernet(key.encode("utf-8") if isinstance(key, str) else key)
    except Exception as e:
        raise CredentialSealError(
            "CREDENTIALS_AT_REST_KEY is not a valid Fernet key"
        ) from e


def seal_secret(plaintext: str | None) -> str:
    """Encrypt when a key is configured; otherwise return plaintext."""
    if not plaintext:
        return plaintext or ""
    f = _fernet()
    if f is None:
        return plaintext
    token = f.encrypt(plaintext.encode("utf-8")).decode("ascii")
    return f"{SEAL_PREFIX}{token}"


def reveal_secret(stored: str | None) -> str:
    """Decrypt enc:v1: values; pass through plaintext."""
    if not stored:
        return ""
    if not stored.startswith(SEAL_PREFIX):
        return stored
    f = _fernet()
    if f is None:
        raise CredentialSealError(
            "Encrypted credential found but CREDENTIALS_AT_REST_KEY is not set"
        )
    blob = stored[len(SEAL_PREFIX) :]
    try:
        return f.decrypt(blob.encode("ascii")).decode("utf-8")
    except InvalidToken as e:
        raise CredentialSealError(
            "Could not decrypt credential; check CREDENTIALS_AT_REST_KEY"
        ) from e
