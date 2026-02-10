import os

import pytest
from telethon import TelegramClient


@pytest.mark.asyncio
async def test_telethon_live_bot_login(tmp_path):
    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")
    bot_token = os.getenv("BOT_TOKEN")
    test_chat_id = os.getenv("TELEGRAM_TEST_CHAT_ID")

    if not api_id or not api_hash or not bot_token:
        pytest.skip("Set API_ID, API_HASH, and BOT_TOKEN to run live Telethon test.")

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
