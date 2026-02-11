"""App settings stored in SQLite (overrides env for MongoDB, etc.)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import aiosqlite

from app.config import settings


def get_setting_sync(key: str) -> str | None:
    """Sync read for use in MongoDB client (avoids async deps)."""
    try:
        conn = sqlite3.connect(settings.sqlite_path)
        cur = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row and row[0] else None
    except sqlite3.OperationalError:
        return None


async def get_setting(db: aiosqlite.Connection, key: str) -> str | None:
    async with db.execute("SELECT value FROM app_settings WHERE key = ?", (key,)) as cur:
        row = await cur.fetchone()
    return row[0] if row and row[0] else None


async def set_setting(db: aiosqlite.Connection, key: str, value: str | None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, ?)
           ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at""",
        (key, value, now),
    )
    await db.commit()


def mask_mongo_uri(uri: str) -> str:
    """Mask password in MongoDB URI for display."""
    if not uri or "://" not in uri:
        return "••••••"
    scheme, rest = uri.split("://", 1)
    if "@" in rest:
        user_pass, host = rest.rsplit("@", 1)
        if ":" in user_pass:
            user, _ = user_pass.split(":", 1)
            return f"{scheme}://{user}:••••@{host}"
    return uri
