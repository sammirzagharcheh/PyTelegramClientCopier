from __future__ import annotations

import asyncio
import datetime
import json
import logging
from typing import Any
from urllib.parse import urlsplit

import aiosqlite
from telethon import events, utils
from telethon.errors import ChatIdInvalidError, FloodWaitError
from telethon.tl.custom.message import Message
from telethon.tl.types import MessageMediaWebPage

from app.services.mapping_service import ChannelMapping, MappingFilter, MappingTransform
from app.telegram.chat_ids import alternate_chat_id
from app.telegram.pipeline_preview import (
    MessagePreview,
    apply_transforms,
    media_type_for_telethon_message,
    passes_filters,
    passes_schedule,
    render_template,
)

logger = logging.getLogger(__name__)


def _event_source_chat_id_for_sync(event: Any) -> int | None:
    """Resolve source chat id for MessageEdited / MessageDeleted (peer shapes vary)."""
    cid = getattr(event, "chat_id", None)
    if cid is not None:
        try:
            return int(cid)
        except (TypeError, ValueError):
            pass
    peer = getattr(event, "peer", None)
    if peer is not None:
        try:
            return int(utils.get_peer_id(peer))
        except Exception:
            return None
    return None


# Aliases for unit tests and legacy imports
_message_media_type = media_type_for_telethon_message
_passes_schedule = passes_schedule
_apply_transforms = apply_transforms


def _mapping_needs_sender_info(filters: list[MappingFilter]) -> bool:
    return any(
        (f.allowed_sender_ids and f.allowed_sender_ids.strip())
        or (f.denied_usernames and f.denied_usernames.strip())
        for f in filters
    )


async def _message_preview_for_filters(
    message: Message,
    mapping: ChannelMapping,
) -> MessagePreview:
    text = message.message or ""
    media_type = media_type_for_telethon_message(message)
    sender_id = getattr(message, "sender_id", None)
    sender_username: str | None = None
    if _mapping_needs_sender_info(mapping.filters):
        try:
            sender = await message.get_sender()
            if sender is not None:
                sender_username = getattr(sender, "username", None)
                if sender_id is None:
                    sender_id = getattr(sender, "id", None)
        except Exception:
            pass
    return MessagePreview(
        text=text,
        media_type=media_type,
        sender_id=sender_id,
        sender_username=sender_username,
    )


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


def _media_rule_matches(rule: MappingTransform, media_type: str) -> bool:
    return rule.rule_type == "media" and _rule_applies_to_media_type(rule, media_type)


def _pick_media_replacement(message: Message, transforms: list[MappingTransform]) -> str | None:
    incoming_has_media = (
        message.media is not None and not isinstance(message.media, MessageMediaWebPage)
    )
    if not incoming_has_media:
        return None
    media_type = media_type_for_telethon_message(message)
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


async def _lookup_dest_msg_id(
    db: aiosqlite.Connection,
    user_id: int,
    source_chat_id: int,
    source_msg_id: int,
    dest_chat_id: int,
) -> int | None:
    async with db.execute(
        "SELECT dest_msg_id FROM dest_message_index "
        "WHERE user_id = ? AND source_chat_id = ? AND source_msg_id = ? AND dest_chat_id = ?",
        (user_id, source_chat_id, source_msg_id, dest_chat_id),
    ) as cur:
        row = await cur.fetchone()
    return int(row[0]) if row else None


async def _save_dest_mapping(
    db: aiosqlite.Connection,
    user_id: int,
    source_chat_id: int,
    source_msg_id: int,
    dest_chat_id: int,
    dest_msg_id: int,
) -> None:
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    await db.execute(
        "INSERT OR REPLACE INTO dest_message_index "
        "(user_id, source_chat_id, source_msg_id, dest_chat_id, dest_msg_id, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, source_chat_id, source_msg_id, dest_chat_id, dest_msg_id, now_utc),
    )
    await db.commit()


async def _fire_copy_webhook(
    mapping: ChannelMapping,
    payload_context: dict[str, Any],
    mongo_db,
) -> None:
    if not mapping.copy_webhook_url or not str(mapping.copy_webhook_url).strip():
        return
    from app.services.http_notify import post_json_webhook

    default_payload = {
        "event": payload_context.get("event"),
        "user_id": payload_context.get("user_id"),
        "mapping_id": payload_context.get("mapping_id"),
        "source_chat_id": payload_context.get("source_chat_id"),
        "dest_chat_id": payload_context.get("dest_chat_id"),
    }
    if "source_msg_id" in payload_context:
        default_payload["source_msg_id"] = payload_context.get("source_msg_id")
    if "source_msg_ids" in payload_context:
        default_payload["source_msg_ids"] = payload_context.get("source_msg_ids")
    if "dest_msg_id" in payload_context:
        default_payload["dest_msg_id"] = payload_context.get("dest_msg_id")
    payload = default_payload
    template = (mapping.copy_webhook_payload_template or "").strip()
    if template:
        try:
            rendered = render_template(template, payload_context)
            loaded = json.loads(rendered)
            if isinstance(loaded, dict):
                payload = loaded
            else:
                logger.warning(
                    "copy webhook payload template must render object mapping_id=%s",
                    mapping.id,
                )
        except Exception as e:
            logger.warning("copy webhook payload template invalid mapping_id=%s: %s", mapping.id, e)

    target_url = str(mapping.copy_webhook_url).strip()
    secret_mode = str(mapping.copy_webhook_secret_mode or "hmac_sha256").strip().lower()
    result = await post_json_webhook(
        target_url,
        mapping.copy_webhook_secret,
        payload,
        secret_mode=secret_mode,
        secret_header_name=mapping.copy_webhook_secret_header_name,
        secret_header_value=mapping.copy_webhook_secret_header_value,
    )
    try:
        parsed = urlsplit(target_url)
        safe_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}" if parsed.scheme and parsed.netloc else target_url
        await mongo_db.webhook_logs.insert_one({
            "timestamp": datetime.datetime.now(datetime.timezone.utc),
            "user_id": payload_context.get("user_id"),
            "mapping_id": payload_context.get("mapping_id"),
            "source_chat_id": payload_context.get("source_chat_id"),
            "dest_chat_id": payload_context.get("dest_chat_id"),
            "event": payload_context.get("event"),
            "request": {
                "url": safe_url,
                "method": "POST",
                "secret_mode": secret_mode,
                "payload_size_bytes": result.get("payload_size_bytes"),
                "body_preview": result.get("request_body_preview"),
            },
            "response": {
                "status_code": result.get("status_code"),
                "status_text": result.get("status_text"),
                "latency_ms": result.get("latency_ms"),
                "content_type": result.get("response_content_type"),
                "body": result.get("response_body"),
                "body_truncated": bool(result.get("response_body_truncated")),
            },
            "success": bool(result.get("success")),
            "error": result.get("error"),
        })
    except Exception as e:
        logger.warning("Failed to write webhook log (non-fatal) mapping_id=%s: %s", mapping.id, e)


def _schedule_album_flush(
    *,
    user_id: int,
    source_chat_id: int,
    grouped_id: int,
    album_tasks: dict[tuple[int, int, int], asyncio.Task],
    album_buffers: dict[tuple[int, int, int], list[dict[str, Any]]],
    flush_coro,
) -> None:
    key = (user_id, source_chat_id, grouped_id)
    old = album_tasks.pop(key, None)
    if old is not None:
        old.cancel()

    async def _debounced() -> None:
        try:
            await asyncio.sleep(0.38)
            await flush_coro(key)
        except asyncio.CancelledError:
            return

    album_tasks[key] = asyncio.create_task(_debounced())


def build_message_handlers(
    user_id: int,
    mappings: list[ChannelMapping],
    db: aiosqlite.Connection,
    mongo_db,
) -> tuple[Any, Any, Any]:
    mapping_by_source: dict[int, list[ChannelMapping]] = {}
    for mapping in mappings:
        cids: list[int] = [mapping.source_chat_id]
        alt = alternate_chat_id(mapping.source_chat_id)
        if alt is not None:
            cids.append(alt)
        for cid in cids:
            mapping_by_source.setdefault(cid, []).append(mapping)

    configured_sources = list(mapping_by_source.keys())
    logged_unknown: set[int] = set()
    any_sync_edits = any(m.sync_edits for m in mappings)
    any_sync_deletes = any(m.sync_deletes for m in mappings)

    album_tasks: dict[tuple[int, int, int], asyncio.Task] = {}
    album_buffers: dict[tuple[int, int, int], list[dict[str, Any]]] = {}

    async def _forward_single_message(
        event: events.NewMessage.Event,
        message: Message,
        matched: list[ChannelMapping],
        *,
        source_chat_id: int,
    ) -> None:
        for mapping in matched:
            preview = await _message_preview_for_filters(message, mapping)
            if not passes_filters(preview, mapping.filters):
                continue
            msg_time = message.date
            if msg_time.tzinfo is None:
                msg_time = msg_time.replace(tzinfo=datetime.timezone.utc)
            else:
                msg_time = msg_time.astimezone(datetime.timezone.utc)
            if not passes_schedule(msg_time, mapping.schedule):
                logger.debug("Skipped (outside schedule) msg_id=%s mapping_id=%s", message.id, mapping.id)
                continue

            source_chat_title = (
                (getattr(event.chat, "title", None) if event.chat else None)
                or mapping.source_chat_title
                or ""
            )
            media_type = preview.media_type
            template_context: dict[str, object] = {
                "original_text": message.message or "",
                "source_chat_id": source_chat_id,
                "dest_chat_id": mapping.dest_chat_id,
                "source_chat_title": source_chat_title,
                "dest_chat_title": mapping.dest_chat_title or "",
                "message_id": message.id,
                "media_type": media_type,
                "date_utc": msg_time.isoformat(),
            }
            transformed_text = apply_transforms(
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

            if mapping.send_delay_ms and mapping.send_delay_ms > 0:
                await asyncio.sleep(mapping.send_delay_ms / 1000.0)

            sent = None
            dest_ids = [mapping.dest_chat_id]
            alt_dest = alternate_chat_id(mapping.dest_chat_id)
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
                except FloodWaitError as fw:
                    logger.warning(
                        "FloodWait mapping_id=%s seconds=%s dest=%s",
                        mapping.id,
                        getattr(fw, "seconds", None),
                        dest_id,
                    )
                    last_err = fw
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
                    mapping.dest_chat_id,
                    dest_ids,
                    last_err,
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
                    dest_title = mapping.dest_chat_title or ""
                    if not dest_title:
                        for dest_id in (mapping.dest_chat_id, alternate_chat_id(mapping.dest_chat_id)):
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
                asyncio.create_task(
                    _fire_copy_webhook(
                        mapping,
                        {
                            "event": "message_copied",
                            "user_id": user_id,
                            "mapping_id": mapping.id,
                            "source_chat_id": source_chat_id,
                            "source_msg_id": message.id,
                            "dest_chat_id": mapping.dest_chat_id,
                            "dest_msg_id": sent.id,
                            "source_chat_title": source_title,
                            "dest_chat_title": dest_title,
                            "media_type": media_type,
                            "date_utc": msg_time.isoformat(),
                            "text": transformed_text,
                        },
                        mongo_db,
                    )
                )

    async def _flush_album_buffer(key: tuple[int, int, int]) -> None:
        batch = album_buffers.pop(key, [])
        album_tasks.pop(key, None)
        if not batch:
            return
        first = batch[0]
        event: events.NewMessage.Event = first["event"]
        matched: list[ChannelMapping] = first["matched"]
        source_chat_id = first["source_chat_id"]
        messages: list[Message] = sorted([b["message"] for b in batch], key=lambda m: m.id)
        if len(messages) == 1:
            await _forward_single_message(
                event, messages[0], matched, source_chat_id=source_chat_id
            )
            return
        for mapping in matched:
            previews = [await _message_preview_for_filters(m, mapping) for m in messages]
            if not all(passes_filters(p, mapping.filters) for p in previews):
                continue
            msg_time = messages[-1].date
            if msg_time.tzinfo is None:
                msg_time = msg_time.replace(tzinfo=datetime.timezone.utc)
            else:
                msg_time = msg_time.astimezone(datetime.timezone.utc)
            if not passes_schedule(msg_time, mapping.schedule):
                continue
            medias = []
            captions: list[str] = []
            for m in messages:
                if m.media and not isinstance(m.media, MessageMediaWebPage):
                    medias.append(m.media)
                captions.append(m.message or "")
            caption = "\n".join(c for c in captions if c).strip() or " "
            source_chat_title = (
                (getattr(event.chat, "title", None) if event.chat else None)
                or mapping.source_chat_title
                or ""
            )
            media_type = "photo" if any(m.photo for m in messages) else media_type_for_telethon_message(messages[0])
            template_context = {
                "original_text": caption,
                "source_chat_id": source_chat_id,
                "dest_chat_id": mapping.dest_chat_id,
                "source_chat_title": source_chat_title,
                "dest_chat_title": mapping.dest_chat_title or "",
                "message_id": messages[0].id,
                "media_type": media_type,
                "date_utc": msg_time.isoformat(),
            }
            transformed_text = apply_transforms(
                caption,
                mapping.transforms,
                context=template_context,
                media_type=media_type,
            )
            reply_to_msg_id = None
            if messages[0].reply_to and messages[0].reply_to.reply_to_msg_id:
                reply_to_msg_id = await _lookup_reply_dest_id(
                    db=db,
                    user_id=user_id,
                    source_chat_id=source_chat_id,
                    source_reply_msg_id=messages[0].reply_to.reply_to_msg_id,
                    dest_chat_id=mapping.dest_chat_id,
                )
            if mapping.send_delay_ms and mapping.send_delay_ms > 0:
                await asyncio.sleep(mapping.send_delay_ms / 1000.0)
            if not medias:
                await _forward_single_message(
                    event, messages[0], [mapping], source_chat_id=source_chat_id
                )
                continue
            dest_ids = [mapping.dest_chat_id]
            alt_dest = alternate_chat_id(mapping.dest_chat_id)
            if alt_dest is not None:
                dest_ids.append(alt_dest)
            sent = None
            for dest_id in dest_ids:
                try:
                    sent = await event.client.send_file(
                        dest_id,
                        medias,
                        caption=transformed_text,
                        reply_to=reply_to_msg_id,
                    )
                    break
                except FloodWaitError as fw:
                    logger.warning(
                        "FloodWait (album) mapping_id=%s seconds=%s",
                        mapping.id,
                        getattr(fw, "seconds", None),
                    )
                    break
                except ChatIdInvalidError:
                    continue
            if sent is None:
                continue
            for m in messages:
                await _save_dest_mapping(
                    db=db,
                    user_id=user_id,
                    source_chat_id=source_chat_id,
                    source_msg_id=m.id,
                    dest_chat_id=mapping.dest_chat_id,
                    dest_msg_id=sent.id,
                )
            try:
                await mongo_db.message_logs.insert_one({
                    "user_id": user_id,
                    "source_chat_id": source_chat_id,
                    "source_msg_id": messages[0].id,
                    "dest_chat_id": mapping.dest_chat_id,
                    "dest_msg_id": sent.id,
                    "source_chat_title": str(source_chat_title or ""),
                    "dest_chat_title": str(mapping.dest_chat_title or ""),
                    "timestamp": messages[0].date,
                    "status": "ok_album",
                })
            except Exception as e:
                logger.warning("Failed to write message log (non-fatal): %s", e)
            asyncio.create_task(
                _fire_copy_webhook(
                    mapping,
                    {
                        "event": "album_copied",
                        "user_id": user_id,
                        "mapping_id": mapping.id,
                        "source_chat_id": source_chat_id,
                        "source_msg_ids": [m.id for m in messages],
                        "dest_chat_id": mapping.dest_chat_id,
                        "dest_msg_id": sent.id,
                        "source_chat_title": str(source_chat_title or ""),
                        "dest_chat_title": str(mapping.dest_chat_title or ""),
                        "media_type": media_type,
                        "date_utc": msg_time.isoformat(),
                        "text": transformed_text,
                    },
                    mongo_db,
                )
            )

    async def _handler(event: events.NewMessage.Event) -> None:
        message = event.message
        if not message:
            return

        source_chat_id = event.chat_id
        candidates = [source_chat_id]
        alt = alternate_chat_id(source_chat_id)
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
                    source_chat_id,
                    configured_sources,
                )
            return
        seen: set[int] = set()
        deduped: list[ChannelMapping] = []
        for mapping in matched:
            if mapping.id in seen:
                continue
            seen.add(mapping.id)
            deduped.append(mapping)
        matched = deduped

        gid = getattr(message, "grouped_id", None)
        if gid is not None:
            key = (user_id, source_chat_id, int(gid))
            album_buffers.setdefault(key, []).append(
                {"event": event, "message": message, "matched": matched, "source_chat_id": source_chat_id}
            )
            _schedule_album_flush(
                user_id=user_id,
                source_chat_id=source_chat_id,
                grouped_id=int(gid),
                album_tasks=album_tasks,
                album_buffers=album_buffers,
                flush_coro=_flush_album_buffer,
            )
            return

        await _forward_single_message(event, message, matched, source_chat_id=source_chat_id)

    async def _edit_handler(event: events.MessageEdited.Event) -> None:
        if not any_sync_edits:
            return
        message = event.message
        if not message:
            return
        source_chat_id = _event_source_chat_id_for_sync(event)
        if source_chat_id is None:
            return
        candidates = [source_chat_id]
        alt = alternate_chat_id(source_chat_id)
        if alt is not None:
            candidates.append(alt)
        matched: list[ChannelMapping] = []
        for cid in candidates:
            if cid in mapping_by_source:
                matched.extend(mapping_by_source[cid])
        seen: set[int] = set()
        for mapping in matched:
            if mapping.id in seen:
                continue
            seen.add(mapping.id)
            if not mapping.sync_edits:
                continue
            preview = await _message_preview_for_filters(message, mapping)
            if not passes_filters(preview, mapping.filters):
                continue
            dest_msg_id = await _lookup_dest_msg_id(
                db, user_id, source_chat_id, message.id, mapping.dest_chat_id
            )
            if dest_msg_id is None:
                continue
            msg_time = message.date
            if msg_time.tzinfo is None:
                msg_time = msg_time.replace(tzinfo=datetime.timezone.utc)
            else:
                msg_time = msg_time.astimezone(datetime.timezone.utc)
            if not passes_schedule(msg_time, mapping.schedule):
                continue
            media_type = preview.media_type
            source_chat_title = (
                (getattr(event.chat, "title", None) if event.chat else None)
                or mapping.source_chat_title
                or ""
            )
            template_context: dict[str, object] = {
                "original_text": message.message or "",
                "source_chat_id": source_chat_id,
                "dest_chat_id": mapping.dest_chat_id,
                "source_chat_title": source_chat_title,
                "dest_chat_title": mapping.dest_chat_title or "",
                "message_id": message.id,
                "media_type": media_type,
                "date_utc": msg_time.isoformat(),
            }
            new_text = apply_transforms(
                message.message or "",
                mapping.transforms,
                context=template_context,
                media_type=media_type,
            )
            dest_ids = [mapping.dest_chat_id]
            alt_d = alternate_chat_id(mapping.dest_chat_id)
            if alt_d is not None:
                dest_ids.append(alt_d)
            if mapping.edit_strategy == "append_notice":
                notice = f"[edited src {message.id}] {new_text}"
                for dest_id in dest_ids:
                    try:
                        await event.client.send_message(dest_id, notice)
                        break
                    except ChatIdInvalidError:
                        continue
                continue
            for dest_id in dest_ids:
                try:
                    await event.client.edit_message(dest_id, dest_msg_id, text=new_text)
                    break
                except Exception as e:
                    logger.warning(
                        "edit_message failed mapping_id=%s sync_edits=1: %s",
                        mapping.id,
                        e,
                    )

    async def _delete_handler(event: events.MessageDeleted.Event) -> None:
        if not any_sync_deletes:
            return
        chat_id = _event_source_chat_id_for_sync(event)
        if chat_id is None:
            return
        candidates = [chat_id]
        alt = alternate_chat_id(chat_id)
        if alt is not None:
            candidates.append(alt)
        matched: list[ChannelMapping] = []
        for cid in candidates:
            if cid in mapping_by_source:
                matched.extend(mapping_by_source[cid])
        seen: set[int] = set()
        for mapping in matched:
            if mapping.id in seen:
                continue
            seen.add(mapping.id)
            if not mapping.sync_deletes:
                continue
            dest_ids = [mapping.dest_chat_id]
            alt_d = alternate_chat_id(mapping.dest_chat_id)
            if alt_d is not None:
                dest_ids.append(alt_d)
            to_delete: list[int] = []
            for mid in event.deleted_ids or []:
                dmid = await _lookup_dest_msg_id(db, user_id, chat_id, int(mid), mapping.dest_chat_id)
                if dmid is not None:
                    to_delete.append(dmid)
            if not to_delete:
                continue
            for dest_id in dest_ids:
                try:
                    await event.client.delete_messages(dest_id, to_delete)
                    break
                except ChatIdInvalidError:
                    continue
                except Exception as e:
                    logger.warning("delete_messages failed mapping_id=%s: %s", mapping.id, e)

    return _handler, _edit_handler, _delete_handler


def build_message_handler(
    user_id: int,
    mappings: list[ChannelMapping],
    db: aiosqlite.Connection,
    mongo_db,
):
    """Backward-compatible: return only the NewMessage handler."""
    h, _, _ = build_message_handlers(user_id, mappings, db, mongo_db)
    return h


def _passes_filters(message: Message, filters: list[MappingFilter]) -> bool:
    """Used by tests; builds preview without async sender resolution."""
    text = getattr(message, "message", None) or getattr(message, "text", None) or ""
    mt = media_type_for_telethon_message(message)
    preview = MessagePreview(text=str(text), media_type=mt)
    return passes_filters(preview, filters)
