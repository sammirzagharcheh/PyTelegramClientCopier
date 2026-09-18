"""Bot client session must not reuse a shared on-disk session name."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.telegram.client_manager import start_bot_client


@pytest.mark.asyncio
async def test_start_bot_client_uses_string_session():
    fake_client = MagicMock()
    fake_client.start = AsyncMock()

    with (
        patch("app.telegram.client_manager.settings") as settings,
        patch("app.telegram.client_manager.TelegramClient", return_value=fake_client) as ctor,
        patch("app.telegram.client_manager.StringSession") as string_session,
    ):
        settings.api_id = 1
        settings.api_hash = "hash"
        string_session.return_value = "mem-session"

        client = await start_bot_client("123456:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw")

    assert client is fake_client
    ctor.assert_called_once()
    assert ctor.call_args[0][0] == "mem-session"
    string_session.assert_called_once_with()
    fake_client.start.assert_awaited_once_with(
        bot_token="123456:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"
    )


@pytest.mark.asyncio
async def test_start_bot_client_persists_string_session(tmp_path):
    fake_client = MagicMock()
    fake_client.start = AsyncMock()
    fake_client.session.save = MagicMock(return_value="SAVEDSESSION")
    path = tmp_path / "5.bot.session"

    with (
        patch("app.telegram.client_manager.settings") as settings,
        patch("app.telegram.client_manager.TelegramClient", return_value=fake_client) as ctor,
        patch("app.telegram.at_rest.settings.credentials_at_rest_key", ""),
    ):
        settings.api_id = 1
        settings.api_hash = "hash"
        await start_bot_client(
            "123456:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw",
            session_path=str(path),
        )

    ctor.assert_called_once()
    fake_client.start.assert_awaited_once()
    assert path.read_text(encoding="utf-8") == "SAVEDSESSION"
