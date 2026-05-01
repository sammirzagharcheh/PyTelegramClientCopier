"""Password hashing utilities using bcrypt directly."""

from __future__ import annotations

import bcrypt


def hash_password(password: str) -> str:
    # bcrypt has a 72-byte limit; truncate to avoid errors
    pw_bytes = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pw_bytes, bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str | bytes | None) -> bool:
    if hashed is None:
        return False
    try:
        if isinstance(hashed, bytes):
            hashed_str = hashed.decode("utf-8").strip()
        else:
            hashed_str = str(hashed).strip()
        pw_bytes = plain.encode("utf-8")[:72]
        return bcrypt.checkpw(pw_bytes, hashed_str.encode("ascii"))
    except (ValueError, TypeError):
        return False
