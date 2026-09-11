"""API key scope catalog and enforcement helpers.

Scopes apply only when authentication used ``X-Api-Key``. JWT sessions rely on
role checks (admin / user / viewer) alone.
"""

from __future__ import annotations

from typing import Iterable, Sequence

# Canonical scopes for external API clients (resource:action).
API_KEY_SCOPES: frozenset[str] = frozenset(
    {
        "mappings:read",
        "mappings:write",
        "accounts:read",
        "accounts:write",
        "workers:read",
        "workers:write",
        "logs:read",
        "stats:read",
        "keys:read",
        "keys:write",
        "webhooks:read",
        "webhooks:write",
    }
)

DEFAULT_API_KEY_SCOPES = "mappings:read,mappings:write"

# Human labels for the panel (stable order).
SCOPE_CHOICES: tuple[tuple[str, str], ...] = (
    ("mappings:read", "Read mappings, filters, transforms, schedules, preview"),
    ("mappings:write", "Create and change mappings and nested rules"),
    ("accounts:read", "List accounts and dialogs"),
    ("accounts:write", "Add, edit, delete accounts and run login"),
    ("workers:read", "List workers"),
    ("workers:write", "Start and stop workers"),
    ("logs:read", "Read message, worker, webhook logs and message index"),
    ("stats:read", "Read dashboard stats"),
    ("keys:read", "List API keys"),
    ("keys:write", "Create and revoke API keys"),
    ("webhooks:read", "List alert webhooks"),
    ("webhooks:write", "Create and delete alert webhooks"),
)


def parse_scopes(raw: str | None) -> list[str]:
    """Split a comma-separated scopes string into a de-duplicated ordered list."""
    if not raw or not str(raw).strip():
        return []
    seen: set[str] = set()
    out: list[str] = []
    for part in str(raw).split(","):
        s = part.strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def validate_scopes(scopes: str | Iterable[str]) -> list[str]:
    """Return normalized scopes or raise ValueError if any are unknown / empty."""
    if isinstance(scopes, str):
        normalized = parse_scopes(scopes)
    else:
        normalized = parse_scopes(",".join(str(s) for s in scopes))
    if not normalized:
        raise ValueError("At least one scope is required")
    unknown = [s for s in normalized if s not in API_KEY_SCOPES]
    if unknown:
        raise ValueError(f"Unknown API key scope(s): {', '.join(unknown)}")
    return normalized


def validate_scopes_string(raw: str | None) -> str:
    """Validate and re-serialize a scopes string."""
    return ",".join(validate_scopes(raw or ""))


def has_any_scope(granted: Sequence[str] | None, needed: Sequence[str]) -> bool:
    """True if granted includes at least one of needed."""
    if not needed:
        return True
    g = set(granted or [])
    return any(s in g for s in needed)


def ensure_api_key_scopes(user: dict, needed: Sequence[str]) -> None:
    """No-op for JWT; for API keys require one of ``needed`` or raise PermissionError."""
    if user.get("auth_via") != "api_key":
        return
    if has_any_scope(user.get("api_key_scopes"), needed):
        return
    needed_list = ", ".join(needed)
    raise PermissionError(f"API key missing required scope (one of: {needed_list})")
