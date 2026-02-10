from __future__ import annotations

import re
from typing import Iterable

import aiosqlite
from telethon import events
from telethon.tl.custom.message import Message

from app.services.mapping_service import ChannelMapping, MappingFilter


def _message_media_type(message: Message) -> str:
    if message.voice:
        return "voice"
    if message.video:
        return "video"
    if message.photo:
        return "photo"
    if message.text or message.message:
        return "text"
    return "other"


def _passes_filters(message: Message, filters: Iterable[MappingFilter]) -> bool:
    if not filters:
        return True

    text = message.message or ""
    media_type = _message_media_type(message)

    for filter_rule in filters:
        if filter_rule.media_types:
            allowed = {part.strip().lower() for part in filter_rule.media_types.split(",") if part.strip()}
            if allowed and media_type not in allowed:
                return False
        if filter_rule.include_text and filter_rule.include_text not in text:
            return False
        if filter_rule.exclude_text and filter_rule.exclude_text in text:
            return False
        if filter_rule.regex_pattern and not re.search(filter_rule.regex_pattern, text):
            return False
    return True


async def _lookup_reply_dest_id(
    db: aiosqlite.Connection,
    user_id: int,
    source_chat_id: int,
    source_reply_msg_id: int,
    dest_chat_id: int,
) -> int | None:
    async with db.execute(
        "SELECT dest_msg_id FROM dest_message_index "
        "WHERE user_id = ? AND source_chat_id = ? AND source_msg_id = ? AND dest_chat_id = ?",
        (user_id, source_chat_id, source_reply_msg_id, dest_chat_id),
    ) as cursor:
        row = await cursor.fetchone()
    return row[0] if row else None


async def _save_dest_mapping(
    db: aiosqlite.Connection,
    user_id: int,
    source_chat_id: int,
    source_msg_id: int,
    dest_chat_id: int,
    dest_msg_id: int,
) -> None:
    await db.execute(
        "INSERT OR REPLACE INTO dest_message_index "
        "(user_id, source_chat_id, source_msg_id, dest_chat_id, dest_msg_id) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, source_chat_id, source_msg_id, dest_chat_id, dest_msg_id),
    )
    await db.commit()


def build_message_handler(
    user_id: int,
    mappings: list[ChannelMapping],
    db: aiosqlite.Connection,
    mongo_db,
):
    mapping_by_source: dict[int, list[ChannelMapping]] = {}
    for mapping in mappings:
        mapping_by_source.setdefault(mapping.source_chat_id, []).append(mapping)

    async def _handler(event: events.NewMessage.Event) -> None:
        message = event.message
        if not message:
            return

        source_chat_id = event.chat_id
        if source_chat_id not in mapping_by_source:
            return

        for mapping in mapping_by_source[source_chat_id]:
            if not _passes_filters(message, mapping.filters):
                continue

            reply_to_msg_id = None
            if message.reply_to and message.reply_to.reply_to_msg_id:
                reply_to_msg_id = await _lookup_reply_dest_id(
                    db=db,
                    user_id=user_id,
                    source_chat_id=source_chat_id,
                    source_reply_msg_id=message.reply_to.reply_to_msg_id,
                    dest_chat_id=mapping.dest_chat_id,
                )

            sent = None
            if message.photo or message.video or message.voice:
                sent = await event.client.send_file(
                    mapping.dest_chat_id,
                    message.media,
                    caption=message.message or "",
                    reply_to=reply_to_msg_id,
                )
            else:
                sent = await event.client.send_message(
                    mapping.dest_chat_id,
                    message.message or "",
                    reply_to=reply_to_msg_id,
                )

            if sent:
                await _save_dest_mapping(
                    db=db,
                    user_id=user_id,
                    source_chat_id=source_chat_id,
                    source_msg_id=message.id,
                    dest_chat_id=mapping.dest_chat_id,
                    dest_msg_id=sent.id,
                )
                await mongo_db.message_logs.insert_one(
                    {
                        "user_id": user_id,
                        "source_chat_id": source_chat_id,
                        "source_msg_id": message.id,
                        "dest_chat_id": mapping.dest_chat_id,
                        "dest_msg_id": sent.id,
                        "timestamp": message.date,
                        "status": "ok",
                    }
                )

    return _handler

