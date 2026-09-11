"""API tests for X-Api-Key scope enforcement."""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.auth import create_access_token
from app.auth.password import hash_password
from app.db.sqlite import get_sqlite


@pytest.fixture
def scope_client(tmp_path):
    from app.config import settings

    settings.sqlite_path = str(tmp_path / "scopes.db")
    settings.media_assets_dir = str(tmp_path / "media")
    settings.testing = True
    from app.web.app import create_app

    app = create_app()
    with TestClient(app) as client:
        client.get("/health")

        async def seed():
            db = await get_sqlite()
            await db.execute(
                "INSERT INTO users (email, role, status, password_hash, name) VALUES (?, ?, ?, ?, ?)",
                ("writer@test.com", "user", "active", hash_password("pass"), "W"),
            )
            await db.execute(
                "INSERT INTO users (email, role, status, password_hash, name) VALUES (?, ?, ?, ?, ?)",
                ("admin@test.com", "admin", "active", hash_password("pass"), "A"),
            )
            await db.execute(
                "INSERT INTO telegram_accounts (user_id, name, type, status, session_path) VALUES (?, ?, ?, ?, ?)",
                (1, "acc", "user", "active", "data/sessions/1/test.session"),
            )
            await db.execute(
                "INSERT INTO channel_mappings (user_id, source_chat_id, dest_chat_id, enabled, telegram_account_id) VALUES (?, ?, ?, ?, ?)",
                (1, 10, 20, 1, 1),
            )
            await db.commit()
            await db.close()

        asyncio.run(seed())
        yield client


@pytest.fixture
def writer_token():
    return create_access_token(sub="writer@test.com", user_id=1, role="user")


@pytest.fixture
def admin_token():
    return create_access_token(sub="admin@test.com", user_id=2, role="admin")


def _create_key(client: TestClient, token: str, name: str, scopes: str) -> str:
    r = client.post(
        "/api/users/me/api-keys",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "scopes": scopes},
    )
    assert r.status_code == 201, r.text
    return r.json()["plain_key"]


def test_create_rejects_unknown_scope(scope_client, writer_token):
    r = scope_client.post(
        "/api/users/me/api-keys",
        headers={"Authorization": f"Bearer {writer_token}"},
        json={"name": "bad", "scopes": "mappings:read,not:a:scope"},
    )
    assert r.status_code == 422


def test_read_scope_can_list_mappings_but_not_create(scope_client, writer_token):
    key = _create_key(scope_client, writer_token, "r", "mappings:read")
    r = scope_client.get("/api/mappings", headers={"X-Api-Key": key})
    assert r.status_code == 200
    r2 = scope_client.post(
        "/api/mappings",
        headers={"X-Api-Key": key},
        json={"source_chat_id": 1, "dest_chat_id": 2},
    )
    assert r2.status_code == 403
    assert "scope" in r2.json()["detail"].lower()


def test_write_scope_can_create_mapping(scope_client, writer_token):
    key = _create_key(scope_client, writer_token, "w", "mappings:read,mappings:write")
    r = scope_client.post(
        "/api/mappings",
        headers={"X-Api-Key": key},
        json={"source_chat_id": 99, "dest_chat_id": 100, "name": "via-key", "telegram_account_id": 1},
    )
    assert r.status_code == 201, r.text


def test_preview_allowed_with_read_scope(scope_client, writer_token):
    key = _create_key(scope_client, writer_token, "p", "mappings:read")
    r = scope_client.post(
        "/api/mappings/1/preview",
        headers={"X-Api-Key": key},
        json={"sample_text": "hi", "media_type": "text"},
    )
    assert r.status_code == 200


def test_workers_write_required_to_start(scope_client, writer_token):
    key = _create_key(scope_client, writer_token, "nw", "mappings:write,workers:read")
    r = scope_client.post(
        "/api/workers/start",
        headers={"X-Api-Key": key},
        json={},
    )
    assert r.status_code == 403


def test_jwt_bypasses_scope_checks(scope_client, writer_token):
    r = scope_client.get(
        "/api/mappings",
        headers={"Authorization": f"Bearer {writer_token}"},
    )
    assert r.status_code == 200
    r2 = scope_client.post(
        "/api/mappings",
        headers={"Authorization": f"Bearer {writer_token}"},
        json={"source_chat_id": 3, "dest_chat_id": 4, "name": "jwt", "telegram_account_id": 1},
    )
    assert r2.status_code == 201


def test_api_key_rejected_on_admin_routes(scope_client, writer_token, admin_token):
    # Create key as admin so role would otherwise allow admin access.
    key = _create_key(
        scope_client,
        admin_token,
        "adm",
        "mappings:read,mappings:write,logs:read,stats:read",
    )
    r = scope_client.get("/api/admin/users", headers={"X-Api-Key": key})
    assert r.status_code == 403
    assert "jwt" in r.json()["detail"].lower() or "admin" in r.json()["detail"].lower()


def test_keys_scope_required_to_list_own_keys(scope_client, writer_token):
    key = _create_key(scope_client, writer_token, "nokeys", "mappings:read")
    r = scope_client.get("/api/users/me/api-keys", headers={"X-Api-Key": key})
    assert r.status_code == 403
    key2 = _create_key(scope_client, writer_token, "withkeys", "keys:read")
    r2 = scope_client.get("/api/users/me/api-keys", headers={"X-Api-Key": key2})
    assert r2.status_code == 200
