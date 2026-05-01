"""API tests for roadmap features: preview, clone, alert webhooks, API keys, viewer, feature flags."""

import asyncio
import hashlib

import pytest
from fastapi.testclient import TestClient

from app.auth.password import hash_password
from app.db.gateway import get_db_connection, init_db


@pytest.fixture
def roadmap_client(tmp_path):
    from app.config import settings

    settings.media_assets_dir = str(tmp_path / "media")
    settings.testing = True
    from app.web.app import create_app

    app = create_app()
    with TestClient(app) as client:
        client.get("/health")

        async def seed():
            await init_db()
            db = await get_db_connection()
            await db.execute(
                "TRUNCATE TABLE mapping_filters, channel_mappings, telegram_accounts, users "
                "RESTART IDENTITY CASCADE"
            )
            await db.execute(
                "INSERT INTO users (id, email, role, status, password_hash, name) VALUES (?, ?, ?, ?, ?, ?)",
                (1, "writer@test.com", "user", "active", hash_password("pass"), "W"),
            )
            await db.execute(
                "INSERT INTO users (id, email, role, status, password_hash, name) VALUES (?, ?, ?, ?, ?, ?)",
                (2, "viewer@test.com", "viewer", "active", hash_password("pass"), "V"),
            )
            await db.execute(
                "INSERT INTO channel_mappings (id, user_id, source_chat_id, dest_chat_id, enabled) VALUES (?, ?, ?, ?, ?)",
                (1, 1, 10, 20, 1),
            )
            await db.execute("SELECT setval('users_id_seq', 2, true)")
            await db.execute("SELECT setval('channel_mappings_id_seq', 1, true)")
            await db.commit()
            await db.close()

        asyncio.run(seed())
        yield client


@pytest.fixture
def writer_token():
    from app.auth import create_access_token

    return create_access_token(sub="writer@test.com", user_id=1, role="user")


@pytest.fixture
def viewer_token():
    from app.auth import create_access_token

    return create_access_token(sub="viewer@test.com", user_id=2, role="viewer")


def test_mapping_preview(roadmap_client, writer_token):
    r = roadmap_client.post(
        "/api/mappings/1/preview",
        headers={"Authorization": f"Bearer {writer_token}"},
        json={"sample_text": "hello world", "media_type": "text"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "passes_filters" in data
    assert "transformed_text" in data


def test_mapping_clone(roadmap_client, writer_token):
    r = roadmap_client.post(
        "/api/mappings/1/clone",
        headers={"Authorization": f"Bearer {writer_token}"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["id"] != 1
    assert "copy" in (data.get("name") or "").lower()


def test_alert_webhook_crud(roadmap_client, writer_token):
    r = roadmap_client.post(
        "/api/users/me/alert-webhooks",
        headers={"Authorization": f"Bearer {writer_token}"},
        json={"url": "https://example.com/hook"},
    )
    assert r.status_code == 201
    wid = r.json()["id"]
    r2 = roadmap_client.get(
        "/api/users/me/alert-webhooks",
        headers={"Authorization": f"Bearer {writer_token}"},
    )
    assert r2.status_code == 200
    assert len(r2.json()) == 1
    r3 = roadmap_client.delete(
        f"/api/users/me/alert-webhooks/{wid}",
        headers={"Authorization": f"Bearer {writer_token}"},
    )
    assert r3.status_code == 200


def test_api_key_auth(roadmap_client, writer_token):
    r = roadmap_client.post(
        "/api/users/me/api-keys",
        headers={"Authorization": f"Bearer {writer_token}"},
        json={"name": "k1", "scopes": "mappings:read"},
    )
    assert r.status_code == 201
    plain = r.json()["plain_key"]
    key_hash = hashlib.sha256(plain.encode()).hexdigest()
    r2 = roadmap_client.get(
        "/api/mappings",
        headers={"X-Api-Key": plain},
    )
    assert r2.status_code == 200


def test_viewer_cannot_create_mapping(roadmap_client, viewer_token):
    r = roadmap_client.post(
        "/api/mappings",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"source_chat_id": 1, "dest_chat_id": 2},
    )
    assert r.status_code == 403


def test_feature_flags_patch(roadmap_client, writer_token):
    r = roadmap_client.patch(
        "/api/users/me/feature-flags",
        headers={"Authorization": f"Bearer {writer_token}"},
        json={"flags": {"beta_edit_sync": True}},
    )
    assert r.status_code == 200
    assert r.json().get("beta_edit_sync") is True
    r2 = roadmap_client.get(
        "/api/users/me/feature-flags",
        headers={"Authorization": f"Bearer {writer_token}"},
    )
    assert r2.status_code == 200
