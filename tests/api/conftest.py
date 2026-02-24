"""API test fixtures: TestClient, seeded DB, JWT tokens."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.auth import create_access_token
from app.auth.password import hash_password
from app.db.sqlite import get_sqlite, init_sqlite


@pytest.fixture
def api_client(tmp_path):
    """Create TestClient with tmp SQLite DB, seeded with user and mapping."""
    from app.config import settings

    settings.sqlite_path = str(tmp_path / "test.db")
    settings.media_assets_dir = str(tmp_path / "media_assets")
    from app.web.app import create_app

    app = create_app()

    with TestClient(app) as client:
        client.get("/health")

        async def seed():
            db = await get_sqlite()
            await db.execute(
                "INSERT INTO users (email, role, status, password_hash, name) VALUES (?, ?, ?, ?, ?)",
                ("user@test.com", "user", "active", hash_password("pass"), "User"),
            )
            await db.execute(
                "INSERT INTO users (email, role, status, password_hash, name) VALUES (?, ?, ?, ?, ?)",
                ("admin@test.com", "admin", "active", hash_password("pass"), "Admin"),
            )
            await db.execute(
                "INSERT INTO users (email, role, status, password_hash, name) VALUES (?, ?, ?, ?, ?)",
                ("other@test.com", "user", "active", hash_password("pass"), "Other"),
            )
            await db.execute(
                "INSERT INTO channel_mappings (user_id, source_chat_id, dest_chat_id, enabled) VALUES (?, ?, ?, ?)",
                (1, 10, 20, 1),
            )
            await db.execute(
                "INSERT INTO channel_mappings (user_id, source_chat_id, dest_chat_id, enabled) VALUES (?, ?, ?, ?)",
                (3, 30, 40, 1),
            )
            session_path = str(tmp_path / "user1.session")
            await db.execute(
                "INSERT INTO telegram_accounts (user_id, type, session_path, status) VALUES (?, ?, ?, ?)",
                (1, "user", session_path, "active"),
            )
            await db.commit()
            await db.close()

        asyncio.run(seed())
        yield client


@pytest.fixture
def user_token():
    return create_access_token(sub="user@test.com", user_id=1, role="user")


@pytest.fixture
def admin_token():
    return create_access_token(sub="admin@test.com", user_id=2, role="admin")
