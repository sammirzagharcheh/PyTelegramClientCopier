"""API tests for channel mapping validation."""

from unittest.mock import AsyncMock, patch

import pytest
from app.telegram.peer_access import PeerAccessDenied


@pytest.fixture
def writer_token(api_client):
    from app.auth import create_access_token

    return create_access_token(sub="user@test.com", user_id=1, role="user")


def _seed_bot(name: str) -> int:
    import asyncio

    async def seed():
        from app.db.sqlite import get_sqlite

        db = await get_sqlite()
        await db.execute(
            "INSERT INTO telegram_accounts (user_id, type, bot_token, status, name) "
            "VALUES (?, 'bot', ?, 'active', ?)",
            (1, "123456:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw", name),
        )
        await db.commit()
        async with db.execute(
            "SELECT id FROM telegram_accounts WHERE name = ?",
            (name,),
        ) as cur:
            row = await cur.fetchone()
        await db.close()
        return row[0]

    return asyncio.run(seed())


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


def test_create_bot_mapping_preflight_ok(api_client, writer_token):
    bot_id = _seed_bot("Preflight Bot")
    with (
        patch("app.web.routers.mappings.restart_workers_for_mapping"),
        patch(
            "app.web.routers.mappings.assert_bot_mapping_access",
            new_callable=AsyncMock,
        ) as mock_preflight,
    ):
        r = api_client.post(
            "/api/mappings",
            headers={"Authorization": f"Bearer {writer_token}"},
            json={
                "source_chat_id": -100501,
                "dest_chat_id": -100502,
                "telegram_account_id": bot_id,
                "name": "bot-preflight-ok",
            },
        )
    assert r.status_code == 201
    mock_preflight.assert_awaited_once()
    assert r.json()["name"] == "bot-preflight-ok"


def test_create_bot_mapping_preflight_denied(api_client, writer_token):
    bot_id = _seed_bot("Denied Bot")
    with (
        patch("app.web.routers.mappings.restart_workers_for_mapping"),
        patch(
            "app.web.routers.mappings.assert_bot_mapping_access",
            new_callable=AsyncMock,
            side_effect=PeerAccessDenied(
                "This bot must be an admin on the source channel to receive posts."
            ),
        ),
    ):
        r = api_client.post(
            "/api/mappings",
            headers={"Authorization": f"Bearer {writer_token}"},
            json={
                "source_chat_id": -100601,
                "dest_chat_id": -100602,
                "telegram_account_id": bot_id,
                "name": "bot-preflight-denied",
            },
        )
    assert r.status_code == 400
    assert "admin on the source channel" in r.json()["detail"].lower()
    listed = api_client.get(
        "/api/mappings",
        headers={"Authorization": f"Bearer {writer_token}"},
    )
    assert listed.status_code == 200
    assert not any(i.get("name") == "bot-preflight-denied" for i in listed.json()["items"])


def test_patch_bot_mapping_preflight_denied(api_client, writer_token):
    bot_id = _seed_bot("Patch Denied Bot")
    with (
        patch("app.web.routers.mappings.restart_workers_for_mapping"),
        patch(
            "app.web.routers.mappings.assert_bot_mapping_access",
            new_callable=AsyncMock,
            side_effect=PeerAccessDenied(
                "This bot cannot post in the destination channel. Grant it post permission."
            ),
        ),
    ):
        r = api_client.patch(
            "/api/mappings/1",
            headers={"Authorization": f"Bearer {writer_token}"},
            json={"telegram_account_id": bot_id},
        )
    assert r.status_code == 400
    assert "cannot post" in r.json()["detail"].lower()
    kept = api_client.get(
        "/api/mappings/1",
        headers={"Authorization": f"Bearer {writer_token}"},
    )
    assert kept.status_code == 200
    assert kept.json()["telegram_account_id"] == 1
