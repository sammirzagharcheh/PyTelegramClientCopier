"""Per-user feature flags stored in SQLite app_settings."""

from __future__ import annotations

import json
from typing import Any

import aiosqlite

from app.services.app_settings import get_setting, set_setting


def _user_key(user_id: int) -> str:
    return f"user_feature_flags_{user_id}"


async def get_user_feature_flags(db: aiosqlite.Connection, user_id: int) -> dict[str, Any]:
    raw = await get_setting(db, _user_key(user_id))
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


async def set_user_feature_flags(
    db: aiosqlite.Connection, user_id: int, flags: dict[str, Any]
) -> dict[str, Any]:
    await set_setting(db, _user_key(user_id), json.dumps(flags))
    return flags


async def user_flag_enabled(db: aiosqlite.Connection, user_id: int, name: str) -> bool:
    flags = await get_user_feature_flags(db, user_id)
    return bool(flags.get(name))
