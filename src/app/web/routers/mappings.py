"""Channel mappings API routes."""

from __future__ import annotations

from datetime import datetime, timezone
import re

from fastapi import APIRouter, HTTPException, status

from app.db.message_index_cleanup import delete_dest_message_index_for_mapping
from app.services.mapping_service import WEEKDAY_COLS, load_mapping_by_id
from app.utils.time import normalize_utc_iso_for_json
from app.telegram.pipeline_preview import (
    MessagePreview,
    apply_transforms,
    passes_filters,
    passes_schedule,
)
from app.web.deps import CurrentUser, Db, WriterUser
from app.web.routers.workers import restart_workers_for_mapping


def _schedule_summary(row: tuple | None) -> str:
    """Compute compact label: 24/7, Mon–Fri 9:00–17:00, or Custom."""
    if not row or all(x is None for x in row):
        return "24/7"
    # Check for business hours: Mon–Fri 9:00–17:00 (UTC)
    biz = ("09:00", "17:00", "09:00", "17:00", "09:00", "17:00", "09:00", "17:00", "09:00", "17:00", None, None, None, None)
    if row == biz:
        return "Mon–Fri 9:00–17:00"
    # Check if all weekdays same
    weekdays = [row[i * 2 : i * 2 + 2] for i in range(7)]
    if len(set(tuple(w) for w in weekdays)) == 1 and weekdays[0] != (None, None):
        s, e = weekdays[0]
        return f"Daily {s or ''}–{e or ''}"
    return "Custom"
from app.web.schemas.mappings import (
    ChannelMappingCreate,
    ChannelMappingUpdate,
    ChannelMappingResponse,
    MappingPreviewRequest,
    MappingPreviewResponse,
)
from app.web.schemas.schedules import ScheduleResponse, ScheduleUpdate

router = APIRouter(prefix="/mappings", tags=["mappings"])
_ALLOWED_WEBHOOK_SECRET_MODES = {"hmac_sha256", "header_value", "none"}
_HEADER_NAME_RE = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")


def _normalize_webhook_secret_mode(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in _ALLOWED_WEBHOOK_SECRET_MODES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="copy_webhook_secret_mode must be one of: hmac_sha256, header_value, none",
        )
    return normalized


def _validate_header_name(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return ""
    if not _HEADER_NAME_RE.fullmatch(cleaned):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook secret header name",
        )
    return cleaned


_ALLOWED_SORT = {"id", "name", "source_chat_id", "dest_chat_id", "enabled", "created_at", "user_id"}


@router.get("")
async def list_mappings(
    db: Db,
    user: CurrentUser,
    user_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "id",
    sort_order: str = "asc",
) -> dict:
    """List channel mappings. Users see own; admins can filter by user_id. Returns paginated {items, total, page, page_size, total_pages}."""
    page_size = min(max(1, page_size), 100)
    page = max(1, page)
    offset = (page - 1) * page_size
    col = sort_by if sort_by in _ALLOWED_SORT else "id"
    direction = "DESC" if sort_order.lower() == "desc" else "ASC"
    order = f"ORDER BY {col} {direction}"

    if user["role"] == "admin" and user_id is not None:
        base = "FROM channel_mappings WHERE user_id = ?"
        params: list = [user_id]
    elif user["role"] == "admin":
        base = "FROM channel_mappings"
        params = []
    else:
        base = "FROM channel_mappings WHERE user_id = ?"
        params = [user["id"]]

    async with db.execute(f"SELECT COUNT(*) {base}", params) as cur:
        total = (await cur.fetchone())[0]

    cols = (
        "id, user_id, source_chat_id, dest_chat_id, name, source_chat_title, dest_chat_title, "
        "enabled, telegram_account_id, created_at, send_delay_ms, sync_edits, edit_strategy, "
        "sync_deletes, copy_webhook_url, copy_webhook_secret, copy_webhook_payload_template, "
        "copy_webhook_secret_header_name, copy_webhook_secret_header_value, copy_webhook_secret_mode"
    )
    params.extend([page_size, offset])
    async with db.execute(
        f"SELECT {cols} {base} {order} LIMIT ? OFFSET ?",
        params,
    ) as cur:
        rows = await cur.fetchall()

    mapping_ids = [r[0] for r in rows]
    schedule_by_mapping: dict[int, tuple | None] = {}
    sched_cols = ", ".join(WEEKDAY_COLS)
    if mapping_ids and rows:
        async with db.execute(
            f"SELECT mapping_id, {sched_cols} FROM mapping_schedules WHERE mapping_id IN ({','.join('?' * len(mapping_ids))})",
            mapping_ids,
        ) as cur:
            mapping_scheds = {r[0]: r[1:15] for r in await cur.fetchall()}
        user_ids = list({r[1] for r in rows})
        user_scheds: dict[int, tuple] = {}
        if user_ids:
            async with db.execute(
                f"SELECT user_id, {sched_cols} FROM user_schedules WHERE user_id IN ({','.join('?' * len(user_ids))})",
                user_ids,
            ) as cur:
                user_scheds = {r[0]: r[1:15] for r in await cur.fetchall()}
        for r in rows:
            mid, uid = r[0], r[1]
            override = mapping_scheds.get(mid)
            user_sched = user_scheds.get(uid)
            sched_row = override if override and any(x is not None for x in override) else (user_sched if user_sched and any(x is not None for x in user_sched) else None)
            schedule_by_mapping[mid] = sched_row

    items = []
    for r in rows:
        mid = r[0]
        sched = schedule_by_mapping.get(mid)
        summary = _schedule_summary(sched) if sched else "24/7"
        secret_raw = r[15]
        header_secret_raw = r[18]
        secret_set = bool(secret_raw and str(secret_raw).strip())
        header_secret_set = bool(header_secret_raw and str(header_secret_raw).strip())
        items.append({
            "id": r[0],
            "user_id": r[1],
            "source_chat_id": r[2],
            "dest_chat_id": r[3],
            "name": r[4],
            "source_chat_title": r[5],
            "dest_chat_title": r[6],
            "enabled": bool(r[7]),
            "telegram_account_id": r[8],
            "created_at": normalize_utc_iso_for_json(r[9]),
            "send_delay_ms": int(r[10] or 0),
            "sync_edits": bool(r[11]),
            "edit_strategy": str(r[12] or "replace_text"),
            "sync_deletes": bool(r[13]),
            "copy_webhook_url": r[14],
            "copy_webhook_secret": None,
            "copy_webhook_payload_template": r[16],
            "copy_webhook_secret_header_name": r[17],
            "copy_webhook_secret_mode": str(r[19] or "hmac_sha256"),
            "webhook_secret_configured": secret_set,
            "webhook_secret_header_configured": header_secret_set,
            "schedule_summary": summary,
        })
    total_pages = max(1, (total + page_size - 1) // page_size) if total else 1
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.post("/schedule/bulk-apply")
async def bulk_apply_schedule(db: Db, user: WriterUser) -> dict:
    """Apply current user's default schedule to all of their mappings."""
    from app.services.mapping_service import WEEKDAY_COLS

    cols = ", ".join(WEEKDAY_COLS)
    async with db.execute(
        f"SELECT {cols} FROM user_schedules WHERE user_id = ?",
        (user["id"],),
    ) as cur:
        user_row = await cur.fetchone()
    if not user_row or all(x is None for x in user_row):
        return {"status": "ok", "updated": 0}
    async with db.execute(
        "SELECT id FROM channel_mappings WHERE user_id = ?",
        (user["id"],),
    ) as cur:
        mapping_ids = [r[0] for r in await cur.fetchall()]
    placeholders = ", ".join("?" for _ in WEEKDAY_COLS)
    for mid in mapping_ids:
        await db.execute(
            f"""INSERT INTO mapping_schedules (mapping_id, {cols})
                VALUES (?, {placeholders})
                ON CONFLICT(mapping_id) DO UPDATE SET {', '.join(f'{c}=excluded.{c}' for c in WEEKDAY_COLS)}""",
            (mid, *user_row),
        )
    await db.commit()
    try:
        # Deduplicate: restart once per unique (user_id, telegram_account_id) to avoid
        # rapid stop/spawn cycles when many mappings share the same account.
        seen: set[tuple[int, int | None]] = set()
        for mid in mapping_ids:
            async with db.execute(
                "SELECT user_id, telegram_account_id FROM channel_mappings WHERE id = ?",
                (mid,),
            ) as cur:
                row = (await cur.fetchone()) or (user["id"], None)
            pair = (row[0], row[1])
            if pair not in seen:
                seen.add(pair)
                await restart_workers_for_mapping(db, row[0], row[1])
    except Exception:
        pass
    return {"status": "ok", "updated": len(mapping_ids)}


@router.post("", response_model=ChannelMappingResponse, status_code=status.HTTP_201_CREATED)
async def create_mapping(
    data: ChannelMappingCreate,
    db: Db,
    user: WriterUser,
) -> dict:
    """Create channel mapping."""
    now = datetime.now(timezone.utc).isoformat()
    async with db.execute(
        """INSERT INTO channel_mappings
           (user_id, source_chat_id, dest_chat_id, name, source_chat_title,
            dest_chat_title, enabled, telegram_account_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
           RETURNING id""",
        (
            user["id"],
            data.source_chat_id,
            data.dest_chat_id,
            data.name or "",
            data.source_chat_title or "",
            data.dest_chat_title or "",
            data.telegram_account_id,
            now,
        ),
    ) as cur:
        inserted = await cur.fetchone()
    await db.commit()
    if not inserted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create mapping",
        )
    mid = int(inserted[0])
    async with db.execute(
        """SELECT id, user_id, source_chat_id, dest_chat_id, name,
                  source_chat_title, dest_chat_title, enabled,
                  telegram_account_id, created_at,
                  send_delay_ms, sync_edits, edit_strategy, sync_deletes,
                  copy_webhook_url, copy_webhook_secret, copy_webhook_payload_template,
                  copy_webhook_secret_header_name, copy_webhook_secret_header_value,
                  copy_webhook_secret_mode
           FROM channel_mappings WHERE id = ?""",
        (mid,),
    ) as cur:
        row = await cur.fetchone()
    result = {
        "id": row[0],
        "user_id": row[1],
        "source_chat_id": row[2],
        "dest_chat_id": row[3],
        "name": row[4],
        "source_chat_title": row[5],
        "dest_chat_title": row[6],
        "enabled": bool(row[7]),
        "telegram_account_id": row[8],
        "created_at": normalize_utc_iso_for_json(row[9]),
        "send_delay_ms": int(row[10] or 0),
        "sync_edits": bool(row[11]),
        "edit_strategy": str(row[12] or "replace_text"),
        "sync_deletes": bool(row[13]),
        "copy_webhook_url": row[14],
        "copy_webhook_secret": row[15],
        "copy_webhook_payload_template": row[16],
        "copy_webhook_secret_header_name": row[17],
        "copy_webhook_secret_mode": str(row[19] or "hmac_sha256"),
        "webhook_secret_header_configured": bool(row[18] and str(row[18]).strip()),
    }
    try:
        await restart_workers_for_mapping(db, row[1], row[8])
    except Exception:
        pass
    return result


@router.get("/{mapping_id}", response_model=ChannelMappingResponse)
async def get_mapping(
    mapping_id: int,
    db: Db,
    user: CurrentUser,
) -> dict:
    """Get channel mapping by ID."""
    async with db.execute(
        """SELECT id, user_id, source_chat_id, dest_chat_id, name,
                  source_chat_title, dest_chat_title, enabled,
                  telegram_account_id, created_at,
                  send_delay_ms, sync_edits, edit_strategy, sync_deletes,
                  copy_webhook_url, copy_webhook_secret, copy_webhook_payload_template,
                  copy_webhook_secret_header_name, copy_webhook_secret_header_value,
                  copy_webhook_secret_mode
           FROM channel_mappings WHERE id = ?""",
        (mapping_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    if user["role"] != "admin" and row[1] != user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return {
        "id": row[0],
        "user_id": row[1],
        "source_chat_id": row[2],
        "dest_chat_id": row[3],
        "name": row[4],
        "source_chat_title": row[5],
        "dest_chat_title": row[6],
        "enabled": bool(row[7]),
        "telegram_account_id": row[8],
        "created_at": normalize_utc_iso_for_json(row[9]),
        "send_delay_ms": int(row[10] or 0),
        "sync_edits": bool(row[11]),
        "edit_strategy": str(row[12] or "replace_text"),
        "sync_deletes": bool(row[13]),
        "copy_webhook_url": row[14],
        "copy_webhook_secret": row[15],
        "copy_webhook_payload_template": row[16],
        "copy_webhook_secret_header_name": row[17],
        "copy_webhook_secret_mode": str(row[19] or "hmac_sha256"),
        "webhook_secret_header_configured": bool(row[18] and str(row[18]).strip()),
    }


@router.patch("/{mapping_id}", response_model=ChannelMappingResponse)
async def update_mapping(
    mapping_id: int,
    data: ChannelMappingUpdate,
    db: Db,
    user: WriterUser,
) -> dict:
    """Update channel mapping."""
    async with db.execute(
        "SELECT id, user_id, source_chat_id, dest_chat_id FROM channel_mappings WHERE id = ?",
        (mapping_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    if user["role"] != "admin" and row[1] != user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    _, mapping_user_id, old_source_chat_id, old_dest_chat_id = row
    changed = False
    routing_changed = (
        (data.source_chat_id is not None and int(data.source_chat_id) != int(old_source_chat_id))
        or (data.dest_chat_id is not None and int(data.dest_chat_id) != int(old_dest_chat_id))
    )
    if routing_changed:
        await delete_dest_message_index_for_mapping(
            db, int(mapping_user_id), int(old_source_chat_id), int(old_dest_chat_id)
        )
        changed = True
    updates = []
    params = []
    if data.name is not None:
        updates.append("name = ?")
        params.append(data.name)
    if data.source_chat_id is not None:
        updates.append("source_chat_id = ?")
        params.append(data.source_chat_id)
    if data.dest_chat_id is not None:
        updates.append("dest_chat_id = ?")
        params.append(data.dest_chat_id)
    if data.enabled is not None:
        updates.append("enabled = ?")
        params.append(1 if data.enabled else 0)
    if data.source_chat_title is not None:
        updates.append("source_chat_title = ?")
        params.append(data.source_chat_title)
    if data.dest_chat_title is not None:
        updates.append("dest_chat_title = ?")
        params.append(data.dest_chat_title)
    if data.send_delay_ms is not None:
        updates.append("send_delay_ms = ?")
        params.append(max(0, int(data.send_delay_ms)))
    if data.sync_edits is not None:
        updates.append("sync_edits = ?")
        params.append(1 if data.sync_edits else 0)
    if data.edit_strategy is not None:
        updates.append("edit_strategy = ?")
        params.append(data.edit_strategy)
    if data.sync_deletes is not None:
        updates.append("sync_deletes = ?")
        params.append(1 if data.sync_deletes else 0)
    if data.copy_webhook_url is not None:
        updates.append("copy_webhook_url = ?")
        params.append(data.copy_webhook_url)
    if data.copy_webhook_secret is not None:
        updates.append("copy_webhook_secret = ?")
        params.append(data.copy_webhook_secret)
    if data.copy_webhook_payload_template is not None:
        updates.append("copy_webhook_payload_template = ?")
        params.append(data.copy_webhook_payload_template)
    if data.copy_webhook_secret_header_name is not None:
        updates.append("copy_webhook_secret_header_name = ?")
        params.append(_validate_header_name(data.copy_webhook_secret_header_name))
    if data.copy_webhook_secret_header_value is not None:
        updates.append("copy_webhook_secret_header_value = ?")
        params.append(data.copy_webhook_secret_header_value)
    if data.copy_webhook_secret_mode is not None:
        updates.append("copy_webhook_secret_mode = ?")
        params.append(_normalize_webhook_secret_mode(data.copy_webhook_secret_mode))
    if updates:
        params.append(mapping_id)
        await db.execute(f"UPDATE channel_mappings SET {', '.join(updates)} WHERE id = ?", params)
        changed = True
    if changed:
        await db.commit()
    async with db.execute(
        """SELECT id, user_id, source_chat_id, dest_chat_id, name,
                  source_chat_title, dest_chat_title, enabled,
                  telegram_account_id, created_at,
                  send_delay_ms, sync_edits, edit_strategy, sync_deletes,
                  copy_webhook_url, copy_webhook_secret, copy_webhook_payload_template,
                  copy_webhook_secret_header_name, copy_webhook_secret_header_value,
                  copy_webhook_secret_mode
           FROM channel_mappings WHERE id = ?""",
        (mapping_id,),
    ) as cur:
        row = await cur.fetchone()
    result = {
        "id": row[0],
        "user_id": row[1],
        "source_chat_id": row[2],
        "dest_chat_id": row[3],
        "name": row[4],
        "source_chat_title": row[5],
        "dest_chat_title": row[6],
        "enabled": bool(row[7]),
        "telegram_account_id": row[8],
        "created_at": normalize_utc_iso_for_json(row[9]),
        "send_delay_ms": int(row[10] or 0),
        "sync_edits": bool(row[11]),
        "edit_strategy": str(row[12] or "replace_text"),
        "sync_deletes": bool(row[13]),
        "copy_webhook_url": row[14],
        "copy_webhook_secret": row[15],
        "copy_webhook_payload_template": row[16],
        "copy_webhook_secret_header_name": row[17],
        "copy_webhook_secret_mode": str(row[19] or "hmac_sha256"),
        "webhook_secret_header_configured": bool(row[18] and str(row[18]).strip()),
    }
    # Reload workers whenever persisted columns changed — not only routing/enabled.
    # Otherwise sync_edits / sync_deletes / edit_strategy / send_delay / webhooks stay stale in memory.
    if updates:
        try:
            await restart_workers_for_mapping(db, row[1], row[8])
        except Exception:
            pass
    return result


@router.post("/{mapping_id}/preview", response_model=MappingPreviewResponse)
async def preview_mapping(
    mapping_id: int,
    data: MappingPreviewRequest,
    db: Db,
    user: CurrentUser,
) -> dict:
    from app.web.mapping_access import get_mapping_scope

    owner_id, _acc = await get_mapping_scope(db, user, mapping_id)
    cm = await load_mapping_by_id(db, owner_id, mapping_id)
    if cm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    preview = MessagePreview(
        text=data.sample_text,
        media_type=(data.media_type or "text").lower(),
        sender_id=data.sender_id,
        sender_username=data.sender_username,
    )
    ok_f = passes_filters(preview, cm.filters)
    now_utc = datetime.now(timezone.utc)
    ok_s = passes_schedule(now_utc, cm.schedule)
    template_context: dict[str, object] = {
        "original_text": data.sample_text,
        "source_chat_id": cm.source_chat_id,
        "dest_chat_id": cm.dest_chat_id,
        "source_chat_title": cm.source_chat_title or "",
        "dest_chat_title": cm.dest_chat_title or "",
        "message_id": 0,
        "media_type": preview.media_type,
        "date_utc": now_utc.isoformat(),
    }
    out_text = apply_transforms(
        data.sample_text,
        cm.transforms,
        context=template_context,
        media_type=preview.media_type,
    )
    return {
        "passes_filters": ok_f,
        "passes_schedule": ok_s,
        "transformed_text": out_text,
    }


@router.post("/{mapping_id}/clone", response_model=ChannelMappingResponse, status_code=status.HTTP_201_CREATED)
async def clone_mapping(
    mapping_id: int,
    db: Db,
    user: WriterUser,
) -> dict:
    from app.web.mapping_access import get_mapping_scope

    owner_id, _acc = await get_mapping_scope(db, user, mapping_id)
    async with db.execute(
        """SELECT id, user_id, source_chat_id, dest_chat_id, name, source_chat_title, dest_chat_title,
                  enabled, telegram_account_id, created_at,
                  send_delay_ms, sync_edits, edit_strategy, sync_deletes,
                  copy_webhook_url, copy_webhook_secret, copy_webhook_payload_template,
                  copy_webhook_secret_header_name, copy_webhook_secret_header_value,
                  copy_webhook_secret_mode
           FROM channel_mappings WHERE id = ? AND user_id = ?""",
        (mapping_id, owner_id),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    now = datetime.now(timezone.utc).isoformat()
    base_name = (row[4] or "").strip() or f"mapping_{mapping_id}"
    new_name = f"{base_name} (copy)"
    async with db.execute(
        """INSERT INTO channel_mappings (
            user_id, source_chat_id, dest_chat_id, name, source_chat_title, dest_chat_title,
            enabled, telegram_account_id, created_at,
            send_delay_ms, sync_edits, edit_strategy, sync_deletes, copy_webhook_url, copy_webhook_secret,
            copy_webhook_payload_template, copy_webhook_secret_header_name, copy_webhook_secret_header_value,
            copy_webhook_secret_mode
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
          RETURNING id""",
        (
            row[1],
            row[2],
            row[3],
            new_name,
            row[5],
            row[6],
            row[7],
            row[8],
            now,
            row[10] or 0,
            row[11] or 0,
            row[12] or "replace_text",
            row[13] or 0,
            row[14],
            row[15],
            row[16],
            row[17],
            row[18],
            row[19] or "hmac_sha256",
        ),
    ) as cur:
        inserted = await cur.fetchone()
    await db.commit()
    if not inserted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clone mapping",
        )
    new_id = int(inserted[0])
    async with db.execute(
        """SELECT id, mapping_id, include_text, exclude_text, media_types, regex_pattern, or_group_id,
               allowed_sender_ids, denied_usernames, min_url_count, max_url_count, required_hashtags
           FROM mapping_filters WHERE mapping_id = ?""",
        (mapping_id,),
    ) as cur2:
        filters = await cur2.fetchall()
    for f in filters:
        await db.execute(
            """INSERT INTO mapping_filters (
                mapping_id, include_text, exclude_text, media_types, regex_pattern, or_group_id,
                allowed_sender_ids, denied_usernames, min_url_count, max_url_count, required_hashtags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                new_id,
                f[2],
                f[3],
                f[4],
                f[5],
                f[6],
                f[7],
                f[8],
                f[9],
                f[10],
                f[11],
            ),
        )
    async with db.execute(
        """SELECT rule_type, find_text, replace_text, regex_pattern, regex_flags,
               replacement_media_asset_id, apply_to_media_types, enabled, priority
           FROM mapping_transform_rules WHERE mapping_id = ? ORDER BY priority ASC, id ASC""",
        (mapping_id,),
    ) as cur3:
        rules = await cur3.fetchall()
    for r in rules:
        await db.execute(
            """INSERT INTO mapping_transform_rules (
                mapping_id, rule_type, find_text, replace_text, regex_pattern, regex_flags,
                replacement_media_asset_id, apply_to_media_types, enabled, priority, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (new_id, r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], now),
        )
    cols = ", ".join(WEEKDAY_COLS)
    async with db.execute(
        f"SELECT {cols} FROM mapping_schedules WHERE mapping_id = ?",
        (mapping_id,),
    ) as cur4:
        sched = await cur4.fetchone()
    if sched and any(x is not None for x in sched):
        placeholders = ", ".join("?" for _ in WEEKDAY_COLS)
        await db.execute(
            f"INSERT INTO mapping_schedules (mapping_id, {cols}) VALUES (?, {placeholders})",
            (new_id, *sched),
        )
    await db.commit()
    try:
        await restart_workers_for_mapping(db, row[1], row[8])
    except Exception:
        pass
    return await get_mapping(new_id, db, user)  # type: ignore[misc]


@router.get("/{mapping_id}/schedule", response_model=ScheduleResponse)
async def get_mapping_schedule(
    mapping_id: int,
    db: Db,
    user: CurrentUser,
) -> dict:
    """Get mapping schedule override. Returns null-like (all None) if using user default."""
    from app.services.mapping_service import WEEKDAY_COLS

    async with db.execute(
        "SELECT user_id FROM channel_mappings WHERE id = ?",
        (mapping_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    if user["role"] != "admin" and row[0] != user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    cols = ", ".join(WEEKDAY_COLS)
    async with db.execute(
        f"SELECT {cols} FROM mapping_schedules WHERE mapping_id = ?",
        (mapping_id,),
    ) as cur:
        sched_row = await cur.fetchone()
    if not sched_row:
        return {c: None for c in WEEKDAY_COLS}
    return dict(zip(WEEKDAY_COLS, sched_row))


@router.put("/{mapping_id}/schedule", response_model=ScheduleResponse)
async def update_mapping_schedule(
    mapping_id: int,
    data: ScheduleUpdate,
    db: Db,
    user: WriterUser,
) -> dict:
    """Set mapping schedule override."""
    from app.services.mapping_service import WEEKDAY_COLS

    async with db.execute(
        "SELECT user_id, telegram_account_id FROM channel_mappings WHERE id = ?",
        (mapping_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    if user["role"] != "admin" and row[0] != user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    cols = ", ".join(WEEKDAY_COLS)
    model_dict = data.model_dump()
    values = [model_dict.get(c) for c in WEEKDAY_COLS]
    placeholders = ", ".join("?" for _ in WEEKDAY_COLS)
    upsert = ", ".join(f"{c}=excluded.{c}" for c in WEEKDAY_COLS)
    await db.execute(
        f"""INSERT INTO mapping_schedules (mapping_id, {cols})
            VALUES (?, {placeholders})
            ON CONFLICT(mapping_id) DO UPDATE SET {upsert}""",
        (mapping_id, *values),
    )
    await db.commit()
    try:
        await restart_workers_for_mapping(db, row[0], row[1])
    except Exception:
        pass
    async with db.execute(
        f"SELECT {cols} FROM mapping_schedules WHERE mapping_id = ?",
        (mapping_id,),
    ) as cur:
        sched_row = await cur.fetchone()
    if not sched_row:
        return {c: None for c in WEEKDAY_COLS}
    return dict(zip(WEEKDAY_COLS, sched_row))


@router.delete("/{mapping_id}/schedule")
async def delete_mapping_schedule(
    mapping_id: int,
    db: Db,
    user: WriterUser,
) -> dict:
    """Remove mapping schedule override (fall back to user default)."""
    async with db.execute(
        "SELECT user_id, telegram_account_id FROM channel_mappings WHERE id = ?",
        (mapping_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    if user["role"] != "admin" and row[0] != user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    await db.execute("DELETE FROM mapping_schedules WHERE mapping_id = ?", (mapping_id,))
    await db.commit()
    try:
        await restart_workers_for_mapping(db, row[0], row[1])
    except Exception:
        pass
    return {"status": "ok"}


@router.delete("/{mapping_id}")
async def delete_mapping(
    mapping_id: int,
    db: Db,
    user: WriterUser,
) -> dict:
    """Delete channel mapping."""
    async with db.execute(
        "SELECT id, user_id, telegram_account_id, source_chat_id, dest_chat_id "
        "FROM channel_mappings WHERE id = ?",
        (mapping_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    if user["role"] != "admin" and row[1] != user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    mapping_user_id, mapping_telegram_account_id = row[1], row[2]
    await delete_dest_message_index_for_mapping(db, int(row[1]), int(row[3]), int(row[4]))
    await db.execute("DELETE FROM mapping_schedules WHERE mapping_id = ?", (mapping_id,))
    await db.execute("DELETE FROM mapping_filters WHERE mapping_id = ?", (mapping_id,))
    await db.execute("DELETE FROM mapping_transform_rules WHERE mapping_id = ?", (mapping_id,))
    await db.execute("DELETE FROM channel_mappings WHERE id = ?", (mapping_id,))
    await db.commit()
    try:
        await restart_workers_for_mapping(db, mapping_user_id, mapping_telegram_account_id)
    except Exception:
        pass
    return {"status": "ok"}
