"""Mapping filters API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.web.deps import CurrentUser, Db, WriterUser
from app.web.mapping_access import get_mapping_scope
from app.web.routers.workers import restart_workers_for_mapping
from app.web.validation.filter_validation import validate_filter_payload
from app.web.schemas.mappings import (
    MappingFilterCreate,
    MappingFilterUpdate,
    MappingFilterResponse,
)

router = APIRouter(prefix="/mappings", tags=["filters"])

_FILTER_COLUMNS = (
    "include_text",
    "exclude_text",
    "media_types",
    "regex_pattern",
    "or_group_id",
    "allowed_sender_ids",
    "denied_usernames",
    "min_url_count",
    "max_url_count",
    "required_hashtags",
)


def _row_to_filter_dict(row: tuple) -> dict:
    return {
        "id": row[0],
        "mapping_id": row[1],
        "include_text": row[2],
        "exclude_text": row[3],
        "media_types": row[4],
        "regex_pattern": row[5],
        "or_group_id": int(row[6]) if row[6] is not None else 0,
        "allowed_sender_ids": row[7] if len(row) > 7 else None,
        "denied_usernames": row[8] if len(row) > 8 else None,
        "min_url_count": row[9] if len(row) > 9 else None,
        "max_url_count": row[10] if len(row) > 10 else None,
        "required_hashtags": row[11] if len(row) > 11 else None,
    }


@router.get("/{mapping_id}/filters", response_model=list[MappingFilterResponse])
async def list_filters(
    mapping_id: int,
    db: Db,
    user: CurrentUser,
) -> list[dict]:
    """List filters for a mapping."""
    await get_mapping_scope(db, user, mapping_id)
    async with db.execute(
        """SELECT id, mapping_id, include_text, exclude_text, media_types, regex_pattern, or_group_id,
               allowed_sender_ids, denied_usernames, min_url_count, max_url_count, required_hashtags
           FROM mapping_filters WHERE mapping_id = ? ORDER BY id""",
        (mapping_id,),
    ) as cur:
        rows = await cur.fetchall()
    return [_row_to_filter_dict(r) for r in rows]


@router.post("/{mapping_id}/filters", response_model=MappingFilterResponse, status_code=status.HTTP_201_CREATED)
async def create_filter(
    mapping_id: int,
    data: MappingFilterCreate,
    db: Db,
    user: WriterUser,
) -> dict:
    """Create filter for a mapping."""
    if data.or_group_id is not None and data.or_group_id < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="or_group_id must be non-negative",
        )
    mapping_user_id, mapping_account_id = await get_mapping_scope(db, user, mapping_id)
    validate_filter_payload(
        include_text=data.include_text,
        exclude_text=data.exclude_text,
        media_types=data.media_types,
        regex_pattern=data.regex_pattern,
        allowed_sender_ids=data.allowed_sender_ids,
        denied_usernames=data.denied_usernames,
        min_url_count=data.min_url_count,
        max_url_count=data.max_url_count,
        required_hashtags=data.required_hashtags,
    )
    ogid = data.or_group_id
    cursor = await db.execute(
        """INSERT INTO mapping_filters (
               mapping_id, include_text, exclude_text, media_types, regex_pattern, or_group_id,
               allowed_sender_ids, denied_usernames, min_url_count, max_url_count, required_hashtags)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            mapping_id,
            data.include_text,
            data.exclude_text,
            data.media_types,
            data.regex_pattern,
            ogid,
            data.allowed_sender_ids,
            data.denied_usernames,
            data.min_url_count,
            data.max_url_count,
            data.required_hashtags,
        ),
    )
    fid = cursor.lastrowid
    if ogid is None:
        await db.execute(
            "UPDATE mapping_filters SET or_group_id = ? WHERE id = ?",
            (fid, fid),
        )
    await db.commit()
    try:
        await restart_workers_for_mapping(db, mapping_user_id, mapping_account_id)
    except Exception:
        pass
    async with db.execute(
        """SELECT id, mapping_id, include_text, exclude_text, media_types, regex_pattern, or_group_id,
               allowed_sender_ids, denied_usernames, min_url_count, max_url_count, required_hashtags
           FROM mapping_filters WHERE id = ?""",
        (fid,),
    ) as cur:
        row = await cur.fetchone()
    assert row is not None
    return _row_to_filter_dict(row)


@router.patch("/{mapping_id}/filters/{filter_id}", response_model=MappingFilterResponse)
async def update_filter(
    mapping_id: int,
    filter_id: int,
    data: MappingFilterUpdate,
    db: Db,
    user: WriterUser,
) -> dict:
    """Update filter."""
    if data.or_group_id is not None and data.or_group_id < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="or_group_id must be non-negative",
        )
    mapping_user_id, mapping_account_id = await get_mapping_scope(db, user, mapping_id)
    async with db.execute(
        "SELECT id FROM mapping_filters WHERE id = ? AND mapping_id = ?",
        (filter_id, mapping_id),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filter not found")

    async with db.execute(
        """SELECT include_text, exclude_text, media_types, regex_pattern, or_group_id,
               allowed_sender_ids, denied_usernames, min_url_count, max_url_count, required_hashtags
           FROM mapping_filters WHERE id = ?""",
        (filter_id,),
    ) as cur:
        current = await cur.fetchone()
    assert current is not None
    merged = {
        "include_text": current[0],
        "exclude_text": current[1],
        "media_types": current[2],
        "regex_pattern": current[3],
        "or_group_id": current[4],
        "allowed_sender_ids": current[5],
        "denied_usernames": current[6],
        "min_url_count": current[7],
        "max_url_count": current[8],
        "required_hashtags": current[9],
    }
    patch = data.model_dump(exclude_unset=True)
    merged.update(patch)
    if "or_group_id" in patch and patch["or_group_id"] is not None and patch["or_group_id"] < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="or_group_id must be non-negative",
        )
    validate_filter_payload(
        include_text=merged["include_text"],
        exclude_text=merged["exclude_text"],
        media_types=merged["media_types"],
        regex_pattern=merged["regex_pattern"],
        allowed_sender_ids=merged["allowed_sender_ids"],
        denied_usernames=merged["denied_usernames"],
        min_url_count=merged["min_url_count"],
        max_url_count=merged["max_url_count"],
        required_hashtags=merged["required_hashtags"],
    )

    updates = []
    params = []
    for col in _FILTER_COLUMNS:
        if col in patch:
            updates.append(f"{col} = ?")
            params.append(patch[col])
    if updates:
        params.append(filter_id)
        await db.execute(f"UPDATE mapping_filters SET {', '.join(updates)} WHERE id = ?", params)
        await db.commit()
        try:
            await restart_workers_for_mapping(db, mapping_user_id, mapping_account_id)
        except Exception:
            pass
    async with db.execute(
        """SELECT id, mapping_id, include_text, exclude_text, media_types, regex_pattern, or_group_id,
               allowed_sender_ids, denied_usernames, min_url_count, max_url_count, required_hashtags
           FROM mapping_filters WHERE id = ?""",
        (filter_id,),
    ) as cur:
        row = await cur.fetchone()
    assert row is not None
    return _row_to_filter_dict(row)


@router.delete("/{mapping_id}/filters/{filter_id}")
async def delete_filter(
    mapping_id: int,
    filter_id: int,
    db: Db,
    user: WriterUser,
) -> dict:
    """Delete filter."""
    mapping_user_id, mapping_account_id = await get_mapping_scope(db, user, mapping_id)
    result = await db.execute(
        "DELETE FROM mapping_filters WHERE id = ? AND mapping_id = ?",
        (filter_id, mapping_id),
    )
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filter not found")
    try:
        await restart_workers_for_mapping(db, mapping_user_id, mapping_account_id)
    except Exception:
        pass
    return {"status": "ok"}
