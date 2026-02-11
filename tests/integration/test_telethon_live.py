import pytest
from telethon import TelegramClient

from app.config import settings


@pytest.mark.asyncio
async def test_telethon_live_bot_login(tmp_path):
    api_id = settings.api_id
    api_hash = settings.api_hash
    bot_token = settings.bot_token
    test_chat_id = settings.telegram_test_chat_id

    if not api_id or not api_hash or not bot_token:
        pytest.skip(
            "Set API_ID, API_HASH, and BOT_TOKEN in .env to run live Telethon test. "
            "Create a bot via @BotFather and add BOT_TOKEN=... to .env."
        )

    session_path = tmp_path / "bot.session"
    client = TelegramClient(str(session_path), int(api_id), api_hash)
    await client.start(bot_token=bot_token)

    try:
        me = await client.get_me()
        assert me is not None
        assert me.bot is True
        if test_chat_id:
            sent = await client.send_message(int(test_chat_id), "Telethon live test message")
            assert sent is not None
    finally:
        await client.disconnect()
