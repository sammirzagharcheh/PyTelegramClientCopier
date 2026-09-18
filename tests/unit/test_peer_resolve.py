"""Parse Telegram peer queries (@username, t.me, numeric)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.telegram.dialog_service import AccountCredentials, TelegramDialogsError
from app.telegram.peer_resolve import InvalidPeerQuery, parse_peer_query, resolve_peer


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("@MyChannel", "MyChannel"),
        ("MyChannel", "MyChannel"),
        ("https://t.me/MyChannel", "MyChannel"),
        ("t.me/MyChannel/12", "MyChannel"),
        ("-1001234567890", -1001234567890),
        (" 42 ", 42),
        ("https://t.me/c/1234567890/5", -1001234567890),
    ],
)
def test_parse_peer_query_ok(raw, expected):
    assert parse_peer_query(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "ab",
        "https://t.me/+AbCdEf",
        "https://t.me/joinchat/AAAA",
        "0",
        "@@@",
    ],
)
def test_parse_peer_query_invalid(raw):
    with pytest.raises(InvalidPeerQuery):
        parse_peer_query(raw)


@pytest.mark.asyncio
async def test_resolve_peer_uses_bot_client_and_disconnects():
    entity = MagicMock()
    entity.title = "News"
    entity.username = "news"
    entity.broadcast = True

    client = MagicMock()
    client.get_entity = AsyncMock(return_value=entity)
    client.disconnect = AsyncMock()

    account = AccountCredentials(
        account_id=5,
        user_id=1,
        account_type="bot",
        session_path=None,
        bot_token="123456:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw",
        status="active",
    )

    with (
        patch(
            "app.telegram.peer_resolve.start_account_client",
            new_callable=AsyncMock,
            return_value=client,
        ) as mock_start,
        patch("app.telegram.peer_resolve.get_peer_id", return_value=-100999),
    ):
        result = await resolve_peer(account, "@newschannel")

    assert result.chat_id == -100999
    assert result.title == "News"
    assert result.username == "news"
    mock_start.assert_awaited_once()
    client.get_entity.assert_awaited_once_with("newschannel")
    client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_peer_unknown_entity_is_telegram_error():
    client = MagicMock()
    client.get_entity = AsyncMock(
        side_effect=ValueError('Cannot find any entity corresponding to "nope"')
    )
    client.disconnect = AsyncMock()
    account = AccountCredentials(
        account_id=5,
        user_id=1,
        account_type="bot",
        session_path=None,
        bot_token="123456:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw",
        status="active",
    )
    with patch(
        "app.telegram.peer_resolve.start_account_client",
        new_callable=AsyncMock,
        return_value=client,
    ):
        with pytest.raises(TelegramDialogsError, match="Cannot find"):
            await resolve_peer(account, "@nopechannel")
    client.disconnect.assert_awaited_once()
