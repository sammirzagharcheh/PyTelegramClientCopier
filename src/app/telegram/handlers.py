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

from app.services.mapping_service import ChannelMapping, MappingFilter, MappingTransform, Schedule
from app.utils.regex import regex_flags_from_string

logger = logging.getLogger(__name__)
_TEMPLATE_TOKEN_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


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


def _rule_applies_to_media_type(rule: MappingTransform, media_type: str) -> bool:
    if not rule.apply_to_media_types:
        return True
    allowed = {
        p.strip().lower()
        for p in rule.apply_to_media_types.split(",")
        if p.strip()
    }
    if not allowed:
        return True
    return media_type in allowed or "any" in allowed or "*" in allowed or "all" in allowed


def _render_template(template: str, context: dict[str, object]) -> str:
    def _sub(match: re.Match[str]) -> str:
        key = match.group(1)
        value = context.get(key, "")
        if value is None:
            return ""
        return str(value)

    return _TEMPLATE_TOKEN_RE.sub(_sub, template)


def _apply_transforms(
    text: str,
    transforms: Iterable[MappingTransform],
    *,
    context: dict[str, object] | None = None,
    media_type: str = "text",
) -> str:
    if not transforms:
        return text
    output = text
    for rule in transforms:
        if not rule.enabled:
            continue
        if rule.rule_type == "media":
            continue
        if not _rule_applies_to_media_type(rule, media_type):
            continue
        if rule.rule_type in {"text", "emoji"}:
            if rule.find_text:
                output = output.replace(rule.find_text, rule.replace_text or "")
            continue
        if rule.rule_type == "regex" and rule.regex_pattern:
            try:
                output = re.sub(
                    rule.regex_pattern,
                    rule.replace_text or "",
                    output,
                    flags=regex_flags_from_string(rule.regex_flags),
                )
            except re.error:
                logger.warning(
                    "Invalid regex transform skipped: rule_id=%s pattern=%r",
                    rule.id,
                    rule.regex_pattern,
                )
            continue
        if rule.rule_type == "template":
            template_context = dict(context or {})
            template_context["text"] = output
            output = _render_template(rule.replace_text or "", template_context)
    return output


def _media_rule_matches(rule: MappingTransform, media_type: str) -> bool:
    return rule.rule_type == "media" and _rule_applies_to_media_type(rule, media_type)


def _pick_media_replacement(message: Message, transforms: Iterable[MappingTransform]) -> str | None:
    incoming_has_media = (
        message.media is not None and not isinstance(message.media, MessageMediaWebPage)
    )
    if not incoming_has_media:
        return None
    media_type = _message_media_type(message)
    for rule in transforms:
        if not rule.enabled:
            continue
        if not _media_rule_matches(rule, media_type):
            continue
        if rule.replacement_media_asset_path:
            return rule.replacement_media_asset_path
    return None


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

            source_chat_title = (
                (getattr(event.chat, "title", None) if event.chat else None)
                or mapping.source_chat_title
                or ""
            )
            media_type = _message_media_type(message)
            template_context = {
                "original_text": message.message or "",
                "source_chat_id": source_chat_id,
                "dest_chat_id": mapping.dest_chat_id,
                "source_chat_title": source_chat_title,
                "dest_chat_title": mapping.dest_chat_title or "",
                "message_id": message.id,
                "media_type": media_type,
                "date_utc": msg_time.isoformat(),
            }
            transformed_text = _apply_transforms(
                message.message or "",
                mapping.transforms,
                context=template_context,
                media_type=media_type,
            )
            replacement_media_path = _pick_media_replacement(message, mapping.transforms)
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
                    incoming_supported_media = (
                        (message.photo or message.video or message.voice)
                        and message.media is not None
                        and not isinstance(message.media, MessageMediaWebPage)
                    )
                    use_file = replacement_media_path is not None or incoming_supported_media
                    if use_file:
                        try:
                            file_payload = (
                                replacement_media_path
                                if replacement_media_path is not None
                                else message.media
                            )
                            sent = await event.client.send_file(
                                dest_id,
                                file_payload,
                                caption=transformed_text,
                                reply_to=reply_to_msg_id,
                            )
                        except (FileNotFoundError, OSError) as e:
                            if replacement_media_path is not None and incoming_supported_media:
                                # Replacement file is missing/unreadable; fall back to the
                                # original incoming media so the message is still forwarded.
                                logger.warning(
                                    "Replacement media missing/unreadable for mapping_id=%s path=%r: %s",
                                    mapping.id,
                                    replacement_media_path,
                                    e,
                                )
                                sent = await event.client.send_file(
                                    dest_id,
                                    message.media,
                                    caption=transformed_text,
                                    reply_to=reply_to_msg_id,
                                )
                            else:
                                # Either no replacement was configured (plain incoming media
                                # failed) or there is no incoming media to fall back to;
                                # drop the media and send text only.
                                use_file = False
                        except TypeError:
                            use_file = False
                    if not use_file:
                        sent = await event.client.send_message(
                            dest_id,
                            transformed_text,
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
                    source_title = str(source_chat_title) if source_chat_title else ""
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

