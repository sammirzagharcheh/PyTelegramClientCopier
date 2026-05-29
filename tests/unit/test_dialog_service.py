"""Unit tests for dialog_service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.telegram.dialog_service import (
    AccountCredentials,
    TelegramDialog,
    clear_dialog_cache,
    list_account_dialogs,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_dialog_cache()
    yield
    clear_dialog_cache()


def _make_dialog(dialog_id: int, name: str, entity):
    d = MagicMock()
    d.id = dialog_id
    d.name = name
    d.entity = entity
    return d


@pytest.mark.asyncio
async def test_list_account_dialogs_maps_types_and_disconnects():
    channel = MagicMock()
    channel.broadcast = True
    channel.username = "mychan"
    channel.title = "My Channel"

    user_entity = MagicMock(spec=["id", "first_name", "last_name", "username", "bot"])
    user_entity.id = 42
    user_entity.first_name = "Alice"
    user_entity.last_name = ""
    user_entity.username = "alice"
    user_entity.bot = False

    dialogs = [
        _make_dialog(-100111, "Channel Title", channel),
        _make_dialog(42, "Alice", user_entity),
    ]

    async def fake_iter(limit=500):
        for d in dialogs:
            yield d

    client = MagicMock()
    client.iter_dialogs = fake_iter
    client.disconnect = AsyncMock()

    account = AccountCredentials(
        account_id=1,
        user_id=1,
        account_type="user",
        session_path="/tmp/u.session",
        bot_token=None,
        status="active",
    )

    with patch(
        "app.telegram.dialog_service.start_user_client",
        new_callable=AsyncMock,
        return_value=client,
    ):
        result = await list_account_dialogs(account, use_cache=False)

    assert len(result) == 2
    assert result[0].chat_id == -100111
    assert result[0].title == "Channel Title"
    assert result[1].chat_id == 42
    assert result[1].title == "Alice"
    client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_account_dialogs_uses_cache():
    async def empty_iter(limit=500):
        return
        yield  # pragma: no cover

    client = MagicMock()
    client.iter_dialogs = empty_iter
    client.disconnect = AsyncMock()

    account = AccountCredentials(
        account_id=2,
        user_id=1,
        account_type="user",
        session_path="/tmp/u.session",
        bot_token=None,
        status="active",
    )

    with patch(
        "app.telegram.dialog_service.start_user_client",
        new_callable=AsyncMock,
        return_value=client,
    ) as mock_start:
        await list_account_dialogs(account, use_cache=True)
        await list_account_dialogs(account, use_cache=True)
    assert mock_start.await_count == 1
