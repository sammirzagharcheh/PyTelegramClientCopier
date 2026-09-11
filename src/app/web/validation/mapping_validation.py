"""Channel mapping create/update validation."""

from __future__ import annotations

import aiosqlite
from fastapi import HTTPException, status

from app.telegram.chat_ids import alternate_chat_id


def normalize_chat_id(chat_id: int) -> int:
    """Prefer full channel form (-100…) when an alternate legacy id exists."""
    alt = alternate_chat_id(chat_id)
    if alt is None:
        return chat_id
    return min(chat_id, alt)


def validate_chat_id_field(chat_id: int, field_name: str) -> int:
    if not isinstance(chat_id, int):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be an integer",
        )
    if chat_id == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be non-zero",
        )
    return normalize_chat_id(chat_id)


def validate_route_pair(source_chat_id: int, dest_chat_id: int) -> tuple[int, int]:
    src = validate_chat_id_field(source_chat_id, "source_chat_id")
    dst = validate_chat_id_field(dest_chat_id, "dest_chat_id")
    if src == dst:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source and destination must be different",
        )
    return src, dst


async def fetch_account_for_user(
    db: aiosqlite.Connection,
    account_id: int,
    user_id: int,
    *,
    is_admin: bool,
) -> tuple:
    """Return telegram_accounts row: id, user_id, type, session_path, bot_token, status."""
    async with db.execute(
        "SELECT id, user_id, type, session_path, bot_token, status FROM telegram_accounts WHERE id = ?",
        (account_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Telegram account not found")
    if not is_admin and row[1] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Telegram account access denied")
    return row


async def validate_telegram_account_id(
    db: aiosqlite.Connection,
    account_id: int,
    user_id: int,
    *,
    is_admin: bool,
) -> None:
    row = await fetch_account_for_user(db, account_id, user_id, is_admin=is_admin)
    if row[5] != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram account must be active",
        )
    acc_type = row[2]
    if acc_type == "user" and not row[3]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram account is not connected",
        )
    if acc_type == "bot" and not row[4]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram account is not connected",
        )


async def ensure_no_duplicate_active_mapping(
    db: aiosqlite.Connection,
    user_id: int,
    source_chat_id: int,
    dest_chat_id: int,
    *,
    exclude_mapping_id: int | None = None,
) -> None:
    """Reject if another enabled mapping uses the same route for this user."""
    query = (
        "SELECT id FROM channel_mappings WHERE user_id = ? AND source_chat_id = ? "
        "AND dest_chat_id = ? AND enabled = 1"
    )
    params: list = [user_id, source_chat_id, dest_chat_id]
    if exclude_mapping_id is not None:
        query += " AND id != ?"
        params.append(exclude_mapping_id)
    async with db.execute(query, params) as cur:
        existing = await cur.fetchone()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Mapping already exists",
        )


async def validate_mapping_create(
    db: aiosqlite.Connection,
    *,
    user_id: int,
    is_admin: bool,
    source_chat_id: int,
    dest_chat_id: int,
    telegram_account_id: int | None,
) -> tuple[int, int, int]:
    if telegram_account_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram account is required",
        )
    await validate_telegram_account_id(
        db, telegram_account_id, user_id, is_admin=is_admin
    )
    src, dst = validate_route_pair(source_chat_id, dest_chat_id)
    await ensure_no_duplicate_active_mapping(db, user_id, src, dst)
    return src, dst, telegram_account_id


async def validate_mapping_update_routing(
    db: aiosqlite.Connection,
    *,
    user_id: int,
    is_admin: bool,
    mapping_id: int,
    current_source: int,
    current_dest: int,
    current_account_id: int | None,
    source_chat_id: int | None,
    dest_chat_id: int | None,
    telegram_account_id: int | None,
) -> tuple[int, int, int | None]:
    src = source_chat_id if source_chat_id is not None else current_source
    dst = dest_chat_id if dest_chat_id is not None else current_dest
    src, dst = validate_route_pair(src, dst)

    account_id = telegram_account_id if telegram_account_id is not None else current_account_id
    if account_id is not None:
        await validate_telegram_account_id(db, account_id, user_id, is_admin=is_admin)

    await ensure_no_duplicate_active_mapping(
        db, user_id, src, dst, exclude_mapping_id=mapping_id
    )
    return src, dst, account_id
