"""Password hashing utilities using bcrypt directly."""

from __future__ import annotations

import bcrypt


def hash_password(password: str) -> str:
    # bcrypt has a 72-byte limit; truncate to avoid errors
    pw_bytes = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pw_bytes, bcrypt.gensalt()).decode("ascii")


def _normalize_bcrypt_hash(hashed: object) -> str | None:
    """Coerce DB/driver types to an ASCII bcrypt hash string, or None if unusable."""
    if hashed is None:
        return None
    if isinstance(hashed, memoryview):
        hashed = hashed.tobytes()
    if isinstance(hashed, (bytes, bytearray)):
        hashed_str = bytes(hashed).decode("utf-8", errors="replace").strip()
    else:
        hashed_str = str(hashed).strip()
    if not hashed_str.startswith("$2"):
        return None
    return hashed_str


def verify_password(plain: str, hashed: str | bytes | None) -> bool:
    if hashed is None:
        return False
    try:
        hashed_str = _normalize_bcrypt_hash(hashed)
        if not hashed_str:
            return False
        pw_bytes = plain.encode("utf-8")[:72]
        return bcrypt.checkpw(pw_bytes, hashed_str.encode("ascii"))
    except (ValueError, TypeError, AttributeError):
        return False
