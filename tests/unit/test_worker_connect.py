"""Worker Telegram client connect: user session vs bot token."""

from unittest.mock import AsyncMock, patch

import pytest

from app.worker import connect_worker_client


@pytest.mark.asyncio
async def test_connect_worker_client_bot_skips_session_copy():
    with (
        patch("app.worker.start_bot_client", new_callable=AsyncMock) as mock_bot,
        patch("app.worker.start_user_client", new_callable=AsyncMock) as mock_user,
        patch("app.worker._worker_session_path") as mock_copy,
    ):
        mock_bot.return_value = object()
        client = await connect_worker_client(
            account_type="bot",
            session_path=None,
            bot_token="123456:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw",
        )
    assert client is mock_bot.return_value
    mock_bot.assert_awaited_once()
    mock_user.assert_not_awaited()
    mock_copy.assert_not_called()


@pytest.mark.asyncio
async def test_connect_worker_client_user_copies_session():
    with (
        patch("app.worker.start_bot_client", new_callable=AsyncMock) as mock_bot,
        patch("app.worker.start_user_client", new_callable=AsyncMock) as mock_user,
        patch("app.worker._worker_session_path", return_value="/tmp/copied.session") as mock_copy,
    ):
        mock_user.return_value = object()
        client = await connect_worker_client(
            account_type="user",
            session_path="/tmp/orig.session",
            bot_token=None,
        )
    assert client is mock_user.return_value
    mock_copy.assert_called_once_with("/tmp/orig.session")
    mock_user.assert_awaited_once_with("/tmp/copied.session")
    mock_bot.assert_not_awaited()
