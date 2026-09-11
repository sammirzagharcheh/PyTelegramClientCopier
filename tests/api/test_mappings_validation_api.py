"""API tests for channel mapping validation."""

from unittest.mock import patch

import pytest


@pytest.fixture
def writer_token(api_client):
    from app.auth import create_access_token

    return create_access_token(sub="user@test.com", user_id=1, role="user")


def test_create_mapping_success(api_client, writer_token):
    with patch("app.web.routers.mappings.restart_workers_for_mapping"):
        r = api_client.post(
            "/api/mappings",
            headers={"Authorization": f"Bearer {writer_token}"},
            json={
                "source_chat_id": -100100,
                "dest_chat_id": -100200,
                "telegram_account_id": 1,
                "source_chat_title": "Src",
                "dest_chat_title": "Dst",
                "name": "Test route",
            },
        )
    assert r.status_code == 201
    data = r.json()
    assert data["telegram_account_id"] == 1
    assert data["source_chat_title"] == "Src"


def test_create_mapping_missing_account(api_client, writer_token):
    r = api_client.post(
        "/api/mappings",
        headers={"Authorization": f"Bearer {writer_token}"},
        json={"source_chat_id": 50, "dest_chat_id": 60},
    )
    assert r.status_code == 422


def test_create_mapping_same_source_dest(api_client, writer_token):
    r = api_client.post(
        "/api/mappings",
        headers={"Authorization": f"Bearer {writer_token}"},
        json={
            "source_chat_id": -100111,
            "dest_chat_id": -100111,
            "telegram_account_id": 1,
        },
    )
    assert r.status_code == 400
    assert "different" in r.json()["detail"].lower()


def test_create_mapping_duplicate_active(api_client, writer_token):
    with patch("app.web.routers.mappings.restart_workers_for_mapping"):
        r = api_client.post(
            "/api/mappings",
            headers={"Authorization": f"Bearer {writer_token}"},
            json={
                "source_chat_id": 10,
                "dest_chat_id": 20,
                "telegram_account_id": 1,
            },
        )
    assert r.status_code == 409
    assert "already exists" in r.json()["detail"].lower()


def test_create_mapping_inactive_account(api_client, writer_token):
    import asyncio

    async def seed():
        from app.db.sqlite import get_sqlite

        db = await get_sqlite()
        await db.execute("UPDATE telegram_accounts SET status = 'inactive' WHERE id = 1")
        await db.commit()
        await db.close()

    asyncio.run(seed())
    r = api_client.post(
        "/api/mappings",
        headers={"Authorization": f"Bearer {writer_token}"},
        json={
            "source_chat_id": -100300,
            "dest_chat_id": -100400,
            "telegram_account_id": 1,
        },
    )
    assert r.status_code == 400
    assert "active" in r.json()["detail"].lower()


def test_patch_mapping_updates_telegram_account(api_client, writer_token):
    import asyncio

    async def seed_second_account():
        from app.db.sqlite import get_sqlite

        db = await get_sqlite()
        await db.execute(
            "INSERT INTO telegram_accounts (user_id, type, session_path, status) VALUES (?, ?, ?, ?)",
            (1, "user", "/tmp/acc2.session", "active"),
        )
        await db.commit()
        async with db.execute("SELECT id FROM telegram_accounts WHERE session_path = ?", ("/tmp/acc2.session",)) as cur:
            row = await cur.fetchone()
        await db.close()
        return row[0]

    acc2 = asyncio.run(seed_second_account())
    with patch("app.web.routers.mappings.restart_workers_for_mapping"):
        r = api_client.patch(
            "/api/mappings/1",
            headers={"Authorization": f"Bearer {writer_token}"},
            json={"telegram_account_id": acc2},
        )
    assert r.status_code == 200
    assert r.json()["telegram_account_id"] == acc2


def test_viewer_cannot_create_mapping(api_client):
    import asyncio

    from app.auth import create_access_token

    async def seed_viewer():
        from app.db.sqlite import get_sqlite
        from app.auth.password import hash_password

        db = await get_sqlite()
        await db.execute(
            "INSERT INTO users (email, role, status, password_hash, name) VALUES (?, ?, ?, ?, ?)",
            ("viewer@test.com", "viewer", "active", hash_password("pass"), "Viewer"),
        )
        await db.commit()
        async with db.execute("SELECT id FROM users WHERE email = ?", ("viewer@test.com",)) as cur:
            uid = (await cur.fetchone())[0]
        await db.close()
        return uid

    uid = asyncio.run(seed_viewer())
    viewer = create_access_token(sub="viewer@test.com", user_id=uid, role="viewer")
    r = api_client.post(
        "/api/mappings",
        headers={"Authorization": f"Bearer {viewer}"},
        json={
            "source_chat_id": 1,
            "dest_chat_id": 2,
            "telegram_account_id": 1,
        },
    )
    assert r.status_code == 403
