"""API test fixtures: TestClient, seeded DB, JWT tokens."""

import asyncio
import os

import pytest
from fastapi.testclient import TestClient

from app.auth import create_access_token
from app.auth.password import hash_password
from app.db.gateway import get_db_connection, init_db

POSTGRES_TEST_DSN = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres")


@pytest.fixture
def api_client(tmp_path):
    """Create TestClient with Postgres DB, seeded with user and mapping."""
    from app.config import settings

    settings.db_backend = "postgres"
    settings.database_url = POSTGRES_TEST_DSN
    settings.media_assets_dir = str(tmp_path / "media_assets")
    settings.testing = True
    from app.web.app import create_app

    app = create_app()

    async def seed():
        await init_db()
        db = await get_db_connection()
        await db.execute("DELETE FROM mapping_transform_rules")
        await db.execute("DELETE FROM mapping_filters")
        await db.execute("DELETE FROM mapping_schedules")
        await db.execute("DELETE FROM user_schedules")
        await db.execute("DELETE FROM worker_registry")
        await db.execute("DELETE FROM user_alert_webhooks")
        await db.execute("DELETE FROM user_api_keys")
        await db.execute("DELETE FROM dest_message_index")
        await db.execute("DELETE FROM refresh_tokens")
        await db.execute("DELETE FROM login_sessions")
        await db.execute("DELETE FROM media_assets")
        await db.execute("DELETE FROM channel_mappings")
        await db.execute("DELETE FROM telegram_accounts")
        await db.execute("DELETE FROM admin_invites")
        await db.execute("DELETE FROM users")
        await db.execute(
            "INSERT INTO users (id, email, role, status, password_hash, name) VALUES (?, ?, ?, ?, ?, ?)",
            (1, "user@test.com", "user", "active", hash_password("pass"), "User"),
        )
        await db.execute(
            "INSERT INTO users (id, email, role, status, password_hash, name) VALUES (?, ?, ?, ?, ?, ?)",
            (2, "admin@test.com", "admin", "active", hash_password("pass"), "Admin"),
        )
        await db.execute(
            "INSERT INTO users (id, email, role, status, password_hash, name) VALUES (?, ?, ?, ?, ?, ?)",
            (3, "other@test.com", "user", "active", hash_password("pass"), "Other"),
        )
        await db.execute(
            "INSERT INTO channel_mappings (id, user_id, source_chat_id, dest_chat_id, enabled) VALUES (?, ?, ?, ?, ?)",
            (1, 1, 10, 20, 1),
        )
        await db.execute(
            "INSERT INTO channel_mappings (id, user_id, source_chat_id, dest_chat_id, enabled) VALUES (?, ?, ?, ?, ?)",
            (2, 3, 30, 40, 1),
        )
        session_path = str((tmp_path / "user1.session").resolve())
        await db.execute(
            "INSERT INTO telegram_accounts (id, user_id, type, session_path, status) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "user", session_path, "active"),
        )
        # Keep IDs deterministic across API tests.
        await db.execute("SELECT setval('users_id_seq', 3, true)")
        await db.execute("SELECT setval('channel_mappings_id_seq', 2, true)")
        await db.execute("SELECT setval('telegram_accounts_id_seq', 1, true)")
        await db.commit()
        await db.close()

    asyncio.run(seed())

    with TestClient(app) as client:
        client.get("/health")
        yield client


@pytest.fixture
def user_token():
    return create_access_token(sub="user@test.com", user_id=1, role="user")


@pytest.fixture
def admin_token():
    return create_access_token(sub="admin@test.com", user_id=2, role="admin")
