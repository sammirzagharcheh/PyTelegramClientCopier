"""API tests for account dialog listing."""

from unittest.mock import AsyncMock, patch

import pytest

from app.telegram.dialog_service import (
    SessionLockedError,
    TelegramDialog,
    TelegramDialogsError,
    clear_dialog_cache,
)


@pytest.fixture(autouse=True)
def _clear_dialog_cache():
    clear_dialog_cache()
    yield
    clear_dialog_cache()


def test_list_dialogs_requires_auth(api_client):
    r = api_client.get("/api/accounts/1/dialogs")
    assert r.status_code == 401


def test_list_dialogs_404_unknown_account(api_client, user_token):
    r = api_client.get(
        "/api/accounts/999/dialogs",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 404


def test_list_dialogs_403_other_user_account(api_client, user_token):
    async def seed_other_account():
        from app.db.sqlite import get_sqlite

        db = await get_sqlite()
        await db.execute(
            "INSERT INTO telegram_accounts (user_id, type, session_path, status) VALUES (?, ?, ?, ?)",
            (3, "user", "/tmp/other.session", "active"),
        )
        await db.commit()
        async with db.execute("SELECT id FROM telegram_accounts WHERE user_id = 3") as cur:
            row = await cur.fetchone()
        await db.close()
        return row[0]

    import asyncio

    account_id = asyncio.run(seed_other_account())
    r = api_client.get(
        f"/api/accounts/{account_id}/dialogs",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 403


def test_list_dialogs_400_inactive_account(api_client, user_token):
    import asyncio

    async def seed():
        from app.db.sqlite import get_sqlite

        db = await get_sqlite()
        await db.execute(
            "UPDATE telegram_accounts SET status = 'inactive' WHERE id = 1",
        )
        await db.commit()
        await db.close()

    asyncio.run(seed())
    r = api_client.get(
        "/api/accounts/1/dialogs",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 400
    assert "active" in r.json()["detail"].lower()


def test_list_dialogs_400_not_connected(api_client, user_token):
    import asyncio

    async def seed():
        from app.db.sqlite import get_sqlite

        db = await get_sqlite()
        await db.execute(
            "UPDATE telegram_accounts SET session_path = NULL WHERE id = 1",
        )
        await db.commit()
        await db.close()

    asyncio.run(seed())
    r = api_client.get(
        "/api/accounts/1/dialogs",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 400
    assert "not connected" in r.json()["detail"].lower()


def test_list_dialogs_200_mocked(api_client, user_token):
    sample = [
        TelegramDialog(
            chat_id=-100123,
            title="Source Channel",
            username="srcchan",
            dialog_type="channel",
        ),
        TelegramDialog(
            chat_id=-100456,
            title="Dest Group",
            username=None,
            dialog_type="group",
        ),
    ]
    with patch(
        "app.web.routers.accounts.list_account_dialogs",
        new_callable=AsyncMock,
        return_value=sample,
    ):
        r = api_client.get(
            "/api/accounts/1/dialogs",
            headers={"Authorization": f"Bearer {user_token}"},
        )
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 2
    assert data["items"][0]["chat_id"] == -100123
    assert data["items"][0]["dialog_type"] == "channel"


def test_list_dialogs_409_session_locked(api_client, user_token):
    with patch(
        "app.web.routers.accounts.list_account_dialogs",
        new_callable=AsyncMock,
        side_effect=SessionLockedError("locked"),
    ):
        r = api_client.get(
            "/api/accounts/1/dialogs",
            headers={"Authorization": f"Bearer {user_token}"},
        )
    assert r.status_code == 409
    assert "worker" in r.json()["detail"].lower()


def test_list_dialogs_502_telegram_failure(api_client, user_token):
    with patch(
        "app.web.routers.accounts.list_account_dialogs",
        new_callable=AsyncMock,
        side_effect=TelegramDialogsError("network"),
    ):
        r = api_client.get(
            "/api/accounts/1/dialogs",
            headers={"Authorization": f"Bearer {user_token}"},
        )
    assert r.status_code == 502


def test_list_accounts_status_active_filter(api_client, user_token):
    import asyncio

    async def seed():
        from app.db.sqlite import get_sqlite

        db = await get_sqlite()
        await db.execute(
            "INSERT INTO telegram_accounts (user_id, type, session_path, status) VALUES (?, ?, ?, ?)",
            (1, "user", "/tmp/inactive.session", "inactive"),
        )
        await db.commit()
        await db.close()

    asyncio.run(seed())
    r = api_client.get(
        "/api/accounts?status=active",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 200
    items = r.json()["items"]
    assert all(i["status"] == "active" for i in items)
    assert len(items) == 1


def test_list_accounts_invalid_status(api_client, user_token):
    r = api_client.get(
        "/api/accounts?status=broken",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 400
