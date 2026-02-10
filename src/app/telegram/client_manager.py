from __future__ import annotations

from telethon import TelegramClient, events

from app.config import settings


async def start_user_client(session_path: str) -> TelegramClient:
    if settings.api_id is None or settings.api_hash is None:
        raise RuntimeError("API_ID and API_HASH must be configured for user sessions.")
    client = TelegramClient(session_path, settings.api_id, settings.api_hash)
    await client.start()
    return client


async def start_bot_client(bot_token: str) -> TelegramClient:
    if settings.api_id is None or settings.api_hash is None:
        raise RuntimeError("API_ID and API_HASH must be configured for bot sessions.")
    client = TelegramClient("bot_session", settings.api_id, settings.api_hash)
    await client.start(bot_token=bot_token)
    return client


def attach_handler(client: TelegramClient, handler) -> None:
    client.add_event_handler(handler, events.NewMessage)

