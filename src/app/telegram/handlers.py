from __future__ import annotations

import datetime
import logging
import re
from typing import Iterable

import aiosqlite
from telethon import events
from telethon.errors import ChatIdInvalidError
from telethon.tl.custom.message import Message
from telethon.tl.types import MessageMediaWebPage

from app.services.mapping_service import ChannelMapping, MappingFilter, Schedule

logger = logging.getLogger(__name__)


def _alternate_chat_id(chat_id: int) -> int | None:
    """Return the alternate format for a Telegram chat ID (legacy vs full channel).
    Channels use -100xxxxxxxxxx, legacy groups use -xxxxxxxxx. Both refer to the same chat.
    """
    if chat_id >= 0:
        return None
    if chat_id <= -1000000000000:
        return chat_id + 1000000000000  # full -> legacy
    return chat_id - 1000000000000  # legacy -> full


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


def _passes_schedule(now_utc: datetime.datetime, schedule: Schedule | None) -> bool:
    """Check if now_utc falls within the schedule for its weekday. All times in UTC HH:MM."""
    if schedule is None or schedule.is_empty():
        return True
    # Python weekday: 0=Monday, 6=Sunday
    weekday = now_utc.weekday()
    start_utc, end_utc = schedule.get_for_weekday(weekday)
    if start_utc is None and end_utc is None:
        return True
    try:
        now_t = now_utc.time()
        start_t = datetime.datetime.strptime(start_utc or "00:00", "%H:%M").time()
        end_t = datetime.datetime.strptime(end_utc or "23:59", "%H:%M").time()
    except (ValueError, TypeError):
        return True
    if start_utc is None:
        return now_t <= end_t
    if end_utc is None:
        return now_t >= start_t
    if start_t <= end_t:
        return start_t <= now_t <= end_t
    # Overnight range (e.g. 22:00–02:00)
    return now_t >= start_t or now_t <= end_t


def _passes_filters(message: Message, filters: Iterable[MappingFilter]) -> bool:
    if not filters:
        return True

    text = message.message or ""
    media_type = _message_media_type(message)
    filter_list = list(filters)

    for filter_rule in filter_list:
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
        cids: list[int] = [mapping.source_chat_id]
        alt = _alternate_chat_id(mapping.source_chat_id)
        if alt is not None:
            cids.append(alt)
        for cid in cids:
            mapping_by_source.setdefault(cid, []).append(mapping)

    configured_sources = list(mapping_by_source.keys())
    logged_unknown: set[int] = set()

    async def _handler(event: events.NewMessage.Event) -> None:
        message = event.message
        if not message:
            return

        source_chat_id = event.chat_id
        candidates = [source_chat_id]
        alt = _alternate_chat_id(source_chat_id)
        if alt is not None:
            candidates.append(alt)
        matched: list[ChannelMapping] = []
        for cid in candidates:
            if cid in mapping_by_source:
                matched.extend(mapping_by_source[cid])
        if not matched:
            if source_chat_id not in logged_unknown:
                logged_unknown.add(source_chat_id)
                logger.info(
                    "Message from chat_id=%s has no mapping (configured: %s). "
                    "Verify source chat ID matches your mapping.",
                    source_chat_id, configured_sources,
                )
            return
        seen: set[int] = set()

        for mapping in matched:
            if mapping.id in seen:
                continue
            seen.add(mapping.id)
            if not _passes_filters(message, mapping.filters):
                continue
            msg_time = message.date
            if msg_time.tzinfo is None:
                msg_time = msg_time.replace(tzinfo=datetime.timezone.utc)
            else:
                msg_time = msg_time.astimezone(datetime.timezone.utc)
            if not _passes_schedule(msg_time, mapping.schedule):
                logger.debug("Skipped (outside schedule) msg_id=%s mapping_id=%s", message.id, mapping.id)
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
            dest_ids = [mapping.dest_chat_id]
            alt_dest = _alternate_chat_id(mapping.dest_chat_id)
            if alt_dest is not None:
                dest_ids.append(alt_dest)
            last_err: Exception | None = None
            for dest_id in dest_ids:
                try:
                    use_file = (
                        (message.photo or message.video or message.voice)
                        and message.media is not None
                        and not isinstance(message.media, MessageMediaWebPage)
                    )
                    if use_file:
                        try:
                            sent = await event.client.send_file(
                                dest_id,
                                message.media,
                                caption=message.message or "",
                                reply_to=reply_to_msg_id,
                            )
                        except TypeError:
                            use_file = False
                    if not use_file:
                        sent = await event.client.send_message(
                            dest_id,
                            message.message or "",
                            reply_to=reply_to_msg_id,
                        )
                    break
                except ChatIdInvalidError as e:
                    last_err = e
                    continue
                except Exception as e:
                    last_err = e
                    raise
            if sent is None and last_err:
                logger.warning(
                    "Failed to send to dest_chat_id=%s (tried %s): %s",
                    mapping.dest_chat_id, dest_ids, last_err,
                )

            if sent:
                logger.info(
                    "Forwarded msg %s from chat %s -> %s",
                    message.id, source_chat_id, mapping.dest_chat_id,
                )
                await _save_dest_mapping(
                    db=db,
                    user_id=user_id,
                    source_chat_id=source_chat_id,
                    source_msg_id=message.id,
                    dest_chat_id=mapping.dest_chat_id,
                    dest_msg_id=sent.id,
                )
                try:
                    source_title = (
                        (getattr(event.chat, "title", None) if event.chat else None)
                        or mapping.source_chat_title
                        or ""
                    )
                    source_title = str(source_title) if source_title else ""
                    # Fetch dest title from Telegram; mapping rarely has it (Add Mapping doesn't set it)
                    dest_title = mapping.dest_chat_title or ""
                    if not dest_title:
                        for dest_id in (mapping.dest_chat_id, _alternate_chat_id(mapping.dest_chat_id)):
                            if dest_id is None:
                                continue
                            try:
                                dest_entity = await event.client.get_entity(dest_id)
                                dest_title = getattr(dest_entity, "title", None) or getattr(dest_entity, "first_name", None) or ""
                                if dest_title:
                                    break
                            except Exception:
                                continue
                    dest_title = str(dest_title) if dest_title else ""
                except Exception:
                    source_title = ""
                    dest_title = ""
                try:
                    await mongo_db.message_logs.insert_one({
                        "user_id": user_id,
                        "source_chat_id": source_chat_id,
                        "source_msg_id": message.id,
                        "dest_chat_id": mapping.dest_chat_id,
                        "dest_msg_id": sent.id,
                        "source_chat_title": source_title,
                        "dest_chat_title": dest_title,
                        "timestamp": message.date,
                        "status": "ok",
                    })
                except Exception as e:
                    logger.warning("Failed to write message log (non-fatal): %s", e)

    return _handler

