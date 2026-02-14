"""Channel mappings API routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.services.mapping_service import WEEKDAY_COLS
from app.web.deps import CurrentUser, Db
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
)
from app.web.schemas.schedules import ScheduleResponse, ScheduleUpdate

router = APIRouter(prefix="/mappings", tags=["mappings"])


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

    cols = "id, user_id, source_chat_id, dest_chat_id, name, source_chat_title, dest_chat_title, enabled, telegram_account_id, created_at"
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
        items.append({
            "id": r[0], "user_id": r[1], "source_chat_id": r[2], "dest_chat_id": r[3],
            "name": r[4], "source_chat_title": r[5], "dest_chat_title": r[6],
            "enabled": bool(r[7]), "telegram_account_id": r[8], "created_at": r[9],
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
async def bulk_apply_schedule(db: Db, user: CurrentUser) -> dict:
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
        for mid in mapping_ids:
            async with db.execute(
                "SELECT user_id, telegram_account_id FROM channel_mappings WHERE id = ?",
                (mid,),
            ) as cur:
                row = (await cur.fetchone()) or (user["id"], None)
            await restart_workers_for_mapping(db, row[0], row[1])
    except Exception:
        pass
    return {"status": "ok", "updated": len(mapping_ids)}


@router.post("", response_model=ChannelMappingResponse, status_code=status.HTTP_201_CREATED)
async def create_mapping(
    data: ChannelMappingCreate,
    db: Db,
    user: CurrentUser,
) -> dict:
    """Create channel mapping."""
    now = datetime.now(timezone.utc).isoformat()
    cursor = await db.execute(
        """INSERT INTO channel_mappings
           (user_id, source_chat_id, dest_chat_id, name, source_chat_title,
            dest_chat_title, enabled, telegram_account_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)""",
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
    )
    await db.commit()
    mid = cursor.lastrowid
    async with db.execute(
        """SELECT id, user_id, source_chat_id, dest_chat_id, name,
                  source_chat_title, dest_chat_title, enabled,
                  telegram_account_id, created_at
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
        "created_at": row[9],
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
                  telegram_account_id, created_at
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
        "created_at": row[9],
    }


@router.patch("/{mapping_id}", response_model=ChannelMappingResponse)
async def update_mapping(
    mapping_id: int,
    data: ChannelMappingUpdate,
    db: Db,
    user: CurrentUser,
) -> dict:
    """Update channel mapping."""
    async with db.execute(
        "SELECT id, user_id FROM channel_mappings WHERE id = ?",
        (mapping_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    if user["role"] != "admin" and row[1] != user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
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
    if updates:
        params.append(mapping_id)
        await db.execute(f"UPDATE channel_mappings SET {', '.join(updates)} WHERE id = ?", params)
        await db.commit()
    async with db.execute(
        """SELECT id, user_id, source_chat_id, dest_chat_id, name,
                  source_chat_title, dest_chat_title, enabled,
                  telegram_account_id, created_at
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
        "created_at": row[9],
    }
    runtime_changed = any(
        x is not None
        for x in (data.enabled, data.source_chat_id, data.dest_chat_id)
    )
    if runtime_changed:
        try:
            await restart_workers_for_mapping(db, row[1], row[8])
        except Exception:
            pass
    return result


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
    user: CurrentUser,
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
    user: CurrentUser,
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
    user: CurrentUser,
) -> dict:
    """Delete channel mapping."""
    async with db.execute(
        "SELECT id, user_id, telegram_account_id FROM channel_mappings WHERE id = ?",
        (mapping_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    if user["role"] != "admin" and row[1] != user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    mapping_user_id, mapping_telegram_account_id = row[1], row[2]
    await db.execute("DELETE FROM mapping_filters WHERE mapping_id = ?", (mapping_id,))
    await db.execute("DELETE FROM channel_mappings WHERE id = ?", (mapping_id,))
    await db.commit()
    try:
        await restart_workers_for_mapping(db, mapping_user_id, mapping_telegram_account_id)
    except Exception:
        pass
    return {"status": "ok"}
