"""Channel mappings API routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.web.deps import CurrentUser, Db
from app.web.schemas.mappings import (
    ChannelMappingCreate,
    ChannelMappingUpdate,
    ChannelMappingResponse,
)

router = APIRouter(prefix="/mappings", tags=["mappings"])


@router.get("", response_model=list[ChannelMappingResponse])
async def list_mappings(
    db: Db,
    user: CurrentUser,
    user_id: int | None = None,
) -> list[dict]:
    """List channel mappings. Users see own; admins can filter by user_id."""
    if user["role"] == "admin" and user_id is not None:
        scope_id = user_id
        query = """SELECT id, user_id, source_chat_id, dest_chat_id, name,
                          source_chat_title, dest_chat_title, enabled,
                          telegram_account_id, created_at
                   FROM channel_mappings WHERE user_id = ? ORDER BY id"""
        params: tuple = (scope_id,)
    elif user["role"] == "admin":
        query = """SELECT id, user_id, source_chat_id, dest_chat_id, name,
                          source_chat_title, dest_chat_title, enabled,
                          telegram_account_id, created_at
                   FROM channel_mappings ORDER BY user_id, id"""
        params = ()
    else:
        query = """SELECT id, user_id, source_chat_id, dest_chat_id, name,
                          source_chat_title, dest_chat_title, enabled,
                          telegram_account_id, created_at
                   FROM channel_mappings WHERE user_id = ? ORDER BY id"""
        params = (user["id"],)
    async with db.execute(query, params) as cur:
        rows = await cur.fetchall()
    return [
        {
            "id": r[0],
            "user_id": r[1],
            "source_chat_id": r[2],
            "dest_chat_id": r[3],
            "name": r[4],
            "source_chat_title": r[5],
            "dest_chat_title": r[6],
            "enabled": bool(r[7]),
            "telegram_account_id": r[8],
            "created_at": r[9],
        }
        for r in rows
    ]


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


@router.delete("/{mapping_id}")
async def delete_mapping(
    mapping_id: int,
    db: Db,
    user: CurrentUser,
) -> dict:
    """Delete channel mapping."""
    async with db.execute(
        "SELECT id, user_id FROM channel_mappings WHERE id = ?",
        (mapping_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    if user["role"] != "admin" and row[1] != user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    await db.execute("DELETE FROM mapping_filters WHERE mapping_id = ?", (mapping_id,))
    await db.execute("DELETE FROM channel_mappings WHERE id = ?", (mapping_id,))
    await db.commit()
    return {"status": "ok"}
