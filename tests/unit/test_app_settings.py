"""Unit tests for app_settings - get_setting_sync treats empty string as unset."""

from __future__ import annotations

import aiosqlite
import pytest

from app.config import settings
from app.db.sqlite import init_sqlite
from app.services.app_settings import get_setting_sync, set_setting


@pytest.mark.asyncio
async def test_get_setting_sync_empty_string_returns_none(tmp_path):
    """When app_settings has empty string for a key, get_setting_sync returns None (fallback to env)."""
    settings.sqlite_path = str(tmp_path / "app_settings_test.db")
    tmp_path.mkdir(parents=True, exist_ok=True)
    await init_sqlite()

    # Manually insert empty string
    db = await aiosqlite.connect(settings.sqlite_path)
    await db.execute(
        "INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        ("mongo_db", ""),
    )
    await db.commit()
    await db.close()

    result = get_setting_sync("mongo_db")
    assert result is None


@pytest.mark.asyncio
async def test_get_setting_sync_whitespace_returns_none(tmp_path):
    """When app_settings has whitespace-only value, get_setting_sync returns None."""
    settings.sqlite_path = str(tmp_path / "app_settings_ws_test.db")
    tmp_path.mkdir(parents=True, exist_ok=True)
    await init_sqlite()

    db = await aiosqlite.connect(settings.sqlite_path)
    await db.execute(
        "INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        ("mongo_db", "   "),
    )
    await db.commit()
    await db.close()

    result = get_setting_sync("mongo_db")
    assert result is None


@pytest.mark.asyncio
async def test_get_setting_sync_valid_value_returns_it(tmp_path):
    """When app_settings has a non-empty value, get_setting_sync returns it."""
    settings.sqlite_path = str(tmp_path / "app_settings_valid_test.db")
    tmp_path.mkdir(parents=True, exist_ok=True)
    await init_sqlite()

    db = await aiosqlite.connect(settings.sqlite_path)
    await set_setting(db, "mongo_db", "telegram_copier_dev")
    await db.close()

    result = get_setting_sync("mongo_db")
    assert result == "telegram_copier_dev"
