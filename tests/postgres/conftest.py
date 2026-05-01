"""PostgreSQL parity fixtures for Phase 4 test migration."""

from __future__ import annotations

import os

import pytest

from app.db.gateway import get_db_connection, init_db

POSTGRES_TEST_DSN = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres")


@pytest.fixture
async def postgres_db(monkeypatch):
    monkeypatch.setattr("app.config.settings.db_backend", "postgres")
    monkeypatch.setattr("app.config.settings.database_url", POSTGRES_TEST_DSN)

    await init_db()
    db = await get_db_connection()
    try:
        await db.execute("DELETE FROM mapping_transform_rules")
        await db.execute("DELETE FROM mapping_filters")
        await db.execute("DELETE FROM mapping_schedules")
        await db.execute("DELETE FROM user_schedules")
        await db.execute("DELETE FROM channel_mappings")
        await db.execute("DELETE FROM telegram_accounts")
        await db.execute("DELETE FROM media_assets")
        await db.execute("DELETE FROM refresh_tokens")
        await db.execute("DELETE FROM login_sessions")
        await db.execute("DELETE FROM worker_registry")
        await db.execute("DELETE FROM user_alert_webhooks")
        await db.execute("DELETE FROM user_api_keys")
        await db.execute("DELETE FROM dest_message_index")
        await db.execute("DELETE FROM admin_invites")
        await db.execute("DELETE FROM users")
        await db.commit()
        yield db
    finally:
        await db.close()
