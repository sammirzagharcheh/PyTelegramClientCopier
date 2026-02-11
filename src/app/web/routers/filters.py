"""Mapping filters API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.web.deps import CurrentUser, Db
from app.web.schemas.mappings import (
    MappingFilterCreate,
    MappingFilterUpdate,
    MappingFilterResponse,
)

router = APIRouter(prefix="/mappings", tags=["filters"])


async def _check_mapping_access(db: Db, user: dict, mapping_id: int) -> None:
    async with db.execute(
        "SELECT user_id FROM channel_mappings WHERE id = ?",
        (mapping_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    if user["role"] != "admin" and row[0] != user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("/{mapping_id}/filters", response_model=list[MappingFilterResponse])
async def list_filters(
    mapping_id: int,
    db: Db,
    user: CurrentUser,
) -> list[dict]:
    """List filters for a mapping."""
    await _check_mapping_access(db, user, mapping_id)
    async with db.execute(
        """SELECT id, mapping_id, include_text, exclude_text, media_types, regex_pattern
           FROM mapping_filters WHERE mapping_id = ? ORDER BY id""",
        (mapping_id,),
    ) as cur:
        rows = await cur.fetchall()
    return [
        {
            "id": r[0],
            "mapping_id": r[1],
            "include_text": r[2],
            "exclude_text": r[3],
            "media_types": r[4],
            "regex_pattern": r[5],
        }
        for r in rows
    ]


@router.post("/{mapping_id}/filters", response_model=MappingFilterResponse, status_code=status.HTTP_201_CREATED)
async def create_filter(
    mapping_id: int,
    data: MappingFilterCreate,
    db: Db,
    user: CurrentUser,
) -> dict:
    """Create filter for a mapping."""
    await _check_mapping_access(db, user, mapping_id)
    cursor = await db.execute(
        """INSERT INTO mapping_filters (mapping_id, include_text, exclude_text, media_types, regex_pattern)
           VALUES (?, ?, ?, ?, ?)""",
        (
            mapping_id,
            data.include_text,
            data.exclude_text,
            data.media_types,
            data.regex_pattern,
        ),
    )
    await db.commit()
    fid = cursor.lastrowid
    async with db.execute(
        "SELECT id, mapping_id, include_text, exclude_text, media_types, regex_pattern FROM mapping_filters WHERE id = ?",
        (fid,),
    ) as cur:
        row = await cur.fetchone()
    return {
        "id": row[0],
        "mapping_id": row[1],
        "include_text": row[2],
        "exclude_text": row[3],
        "media_types": row[4],
        "regex_pattern": row[5],
    }


@router.patch("/{mapping_id}/filters/{filter_id}", response_model=MappingFilterResponse)
async def update_filter(
    mapping_id: int,
    filter_id: int,
    data: MappingFilterUpdate,
    db: Db,
    user: CurrentUser,
) -> dict:
    """Update filter."""
    await _check_mapping_access(db, user, mapping_id)
    async with db.execute(
        "SELECT id FROM mapping_filters WHERE id = ? AND mapping_id = ?",
        (filter_id, mapping_id),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filter not found")
    updates = []
    params = []
    if data.include_text is not None:
        updates.append("include_text = ?")
        params.append(data.include_text)
    if data.exclude_text is not None:
        updates.append("exclude_text = ?")
        params.append(data.exclude_text)
    if data.media_types is not None:
        updates.append("media_types = ?")
        params.append(data.media_types)
    if data.regex_pattern is not None:
        updates.append("regex_pattern = ?")
        params.append(data.regex_pattern)
    if updates:
        params.append(filter_id)
        await db.execute(f"UPDATE mapping_filters SET {', '.join(updates)} WHERE id = ?", params)
        await db.commit()
    async with db.execute(
        "SELECT id, mapping_id, include_text, exclude_text, media_types, regex_pattern FROM mapping_filters WHERE id = ?",
        (filter_id,),
    ) as cur:
        row = await cur.fetchone()
    return {
        "id": row[0],
        "mapping_id": row[1],
        "include_text": row[2],
        "exclude_text": row[3],
        "media_types": row[4],
        "regex_pattern": row[5],
    }


@router.delete("/{mapping_id}/filters/{filter_id}")
async def delete_filter(
    mapping_id: int,
    filter_id: int,
    db: Db,
    user: CurrentUser,
) -> dict:
    """Delete filter."""
    await _check_mapping_access(db, user, mapping_id)
    result = await db.execute(
        "DELETE FROM mapping_filters WHERE id = ? AND mapping_id = ?",
        (filter_id, mapping_id),
    )
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filter not found")
    return {"status": "ok"}
