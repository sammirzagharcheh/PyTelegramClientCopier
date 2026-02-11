from __future__ import annotations

import asyncio
import sqlite3

from telethon import TelegramClient, events

from app.config import settings


async def start_user_client(session_path: str) -> TelegramClient:
    if settings.api_id is None or settings.api_hash is None:
        raise RuntimeError("API_ID and API_HASH must be configured for user sessions.")
    client = TelegramClient(session_path, settings.api_id, settings.api_hash)

    for attempt in range(3):
        try:
            await client.start()
            return client
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < 2:
                await asyncio.sleep(2 * (attempt + 1))
            else:
                raise


async def start_bot_client(bot_token: str) -> TelegramClient:
    if settings.api_id is None or settings.api_hash is None:
        raise RuntimeError("API_ID and API_HASH must be configured for bot sessions.")
    client = TelegramClient("bot_session", settings.api_id, settings.api_hash)
    await client.start(bot_token=bot_token)
    return client


def attach_handler(client: TelegramClient, handler) -> None:
    client.add_event_handler(handler, events.NewMessage)

