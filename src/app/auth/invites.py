"""Admin invite tokens (hashed at rest)."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone


def hash_invite_token(token: str) -> str:
    return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()


def generate_invite_token() -> str:
    return secrets.token_urlsafe(32)


def parse_iso_utc(value: str) -> datetime:
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def invite_is_expired(expires_at: str, *, now: datetime | None = None) -> bool:
    current = now or datetime.now(timezone.utc)
    return parse_iso_utc(expires_at) <= current
