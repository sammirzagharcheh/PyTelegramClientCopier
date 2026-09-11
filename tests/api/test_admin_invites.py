"""API tests for admin invites and public accept flow."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.auth import create_access_token
from app.auth.invites import hash_invite_token
from app.auth.password import hash_password
from app.db.sqlite import get_sqlite


@pytest.fixture
def invite_client(tmp_path):
    from app.config import settings

    settings.sqlite_path = str(tmp_path / "invites.db")
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
                ("admin@test.com", "admin", "active", hash_password("pass"), "A"),
            )
            await db.execute(
                "INSERT INTO users (email, role, status, password_hash, name) VALUES (?, ?, ?, ?, ?)",
                ("writer@test.com", "user", "active", hash_password("pass"), "W"),
            )
            await db.commit()
            await db.close()

        asyncio.run(seed())
        yield client


@pytest.fixture
def admin_token():
    return create_access_token(sub="admin@test.com", user_id=1, role="admin")


@pytest.fixture
def writer_token():
    return create_access_token(sub="writer@test.com", user_id=2, role="user")


def test_non_admin_cannot_create_invite(invite_client, writer_token):
    r = invite_client.post(
        "/api/admin/invites",
        headers={"Authorization": f"Bearer {writer_token}"},
        json={"email": "new@test.com", "role": "user"},
    )
    assert r.status_code == 403


def test_create_list_accept_invite(invite_client, admin_token):
    r = invite_client.post(
        "/api/admin/invites",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"email": "new@test.com", "role": "viewer", "expires_in_hours": 48},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["email"] == "new@test.com"
    assert data["role"] == "viewer"
    assert data["plain_token"]
    assert data["invite_path"].startswith("/invite/")
    token = data["plain_token"]

    listed = invite_client.get(
        "/api/admin/invites",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert listed.status_code == 200
    assert any(i["email"] == "new@test.com" and i["status"] == "pending" for i in listed.json())

    preview = invite_client.get(f"/api/auth/invites/{token}")
    assert preview.status_code == 200
    assert preview.json()["email"] == "new@test.com"
    assert preview.json()["role"] == "viewer"

    accept = invite_client.post(
        f"/api/auth/invites/{token}/accept",
        json={"password": "password12", "name": "New User"},
    )
    assert accept.status_code == 200, accept.text
    assert accept.json()["access_token"]
    assert accept.json()["refresh_token"]

    # Token spent
    again = invite_client.get(f"/api/auth/invites/{token}")
    assert again.status_code == 410

    login = invite_client.post(
        "/api/auth/login",
        json={"email": "new@test.com", "password": "password12"},
    )
    assert login.status_code == 200


def test_accept_rejects_short_password(invite_client, admin_token):
    r = invite_client.post(
        "/api/admin/invites",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"email": "short@test.com", "role": "user"},
    )
    token = r.json()["plain_token"]
    bad = invite_client.post(
        f"/api/auth/invites/{token}/accept",
        json={"password": "short"},
    )
    assert bad.status_code == 400


def test_create_invite_conflicts_existing_user(invite_client, admin_token):
    r = invite_client.post(
        "/api/admin/invites",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"email": "writer@test.com", "role": "user"},
    )
    assert r.status_code == 409


def test_expired_invite_gone(invite_client, admin_token):
    r = invite_client.post(
        "/api/admin/invites",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"email": "late@test.com", "role": "user"},
    )
    token = r.json()["plain_token"]
    invite_id = r.json()["id"]

    async def expire():
        db = await get_sqlite()
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        await db.execute(
            "UPDATE admin_invites SET expires_at = ? WHERE id = ?",
            (past, invite_id),
        )
        await db.commit()
        await db.close()

    asyncio.run(expire())
    preview = invite_client.get(f"/api/auth/invites/{token}")
    assert preview.status_code == 410


def test_revoke_invite(invite_client, admin_token):
    r = invite_client.post(
        "/api/admin/invites",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"email": "rev@test.com", "role": "user"},
    )
    invite_id = r.json()["id"]
    token = r.json()["plain_token"]
    deleted = invite_client.delete(
        f"/api/admin/invites/{invite_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert deleted.status_code == 200
    assert invite_client.get(f"/api/auth/invites/{token}").status_code == 404


def test_token_stored_hashed(invite_client, admin_token):
    r = invite_client.post(
        "/api/admin/invites",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"email": "hash@test.com", "role": "user"},
    )
    plain = r.json()["plain_token"]
    invite_id = r.json()["id"]

    async def read_hash():
        db = await get_sqlite()
        async with db.execute(
            "SELECT token_hash FROM admin_invites WHERE id = ?",
            (invite_id,),
        ) as cur:
            row = await cur.fetchone()
        await db.close()
        return row[0]

    stored = asyncio.run(read_hash())
    assert stored == hash_invite_token(plain)
    assert stored != plain
