"""Telegram accounts API routes."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form

from app.config import settings
from app.web.schemas.accounts import TelegramAccountUpdate
from app.web.deps import AdminUser, CurrentUser, Db
from app.web.routers.workers import stop_workers_for_account

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("")
async def list_accounts(
    db: Db,
    user: CurrentUser,
    user_id: int | None = None,
) -> list[dict]:
    """List telegram accounts. Users see own; admins can filter by user_id."""
    if user["role"] == "admin":
        if user_id is not None:
            scope_id = user_id
        else:
            scope_id = -1
        if scope_id == -1:
            query = "SELECT id, user_id, name, type, session_path, phone, status, created_at FROM telegram_accounts ORDER BY user_id, id"
            params: tuple = ()
        else:
            query = "SELECT id, user_id, name, type, session_path, phone, status, created_at FROM telegram_accounts WHERE user_id = ? ORDER BY id"
            params = (scope_id,)
    else:
        query = "SELECT id, user_id, name, type, session_path, phone, status, created_at FROM telegram_accounts WHERE user_id = ? ORDER BY id"
        params = (user["id"],)
    async with db.execute(query, params) as cur:
        rows = await cur.fetchall()
    return [
        {
            "id": r[0],
            "user_id": r[1],
            "name": r[2],
            "type": r[3],
            "session_path": r[4],
            "phone": r[5],
            "status": r[6],
            "created_at": r[7],
        }
        for r in rows
    ]


@router.get("/{account_id}")
async def get_account(
    account_id: int,
    db: Db,
    user: CurrentUser,
) -> dict:
    """Get telegram account by ID."""
    async with db.execute(
        "SELECT id, user_id, name, type, session_path, phone, status, created_at FROM telegram_accounts WHERE id = ?",
        (account_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if user["role"] != "admin" and row[1] != user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return {
        "id": row[0],
        "user_id": row[1],
        "name": row[2],
        "type": row[3],
        "session_path": row[4],
        "phone": row[5],
        "status": row[6],
        "created_at": row[7],
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_account(
    db: Db,
    user: CurrentUser,
    name: str = Form(...),
    type: str = Form(...),
    bot_token: str | None = Form(None),
    session_file: UploadFile | None = File(None),
) -> dict:
    """Create telegram account. For type=user, upload session file. For type=bot, provide bot_token."""
    if type not in ("user", "bot"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="type must be 'user' or 'bot'")
    if type == "bot" and not bot_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="bot_token required for bot accounts")
    if type == "user" and not session_file:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="session_file required for user accounts")
    now = datetime.now(timezone.utc).isoformat()
    session_path = None
    phone = None
    if type == "user" and session_file:
        cursor = await db.execute(
            """INSERT INTO telegram_accounts (user_id, type, status, name, created_at)
               VALUES (?, 'user', 'active', ?, ?)""",
            (user["id"], name or "User account", now),
        )
        await db.commit()
        acc_id = cursor.lastrowid
        sessions_base = Path(settings.sessions_dir) / str(user["id"])
        sessions_base.mkdir(parents=True, exist_ok=True)
        ext = Path(session_file.filename or "").suffix or ".session"
        dest_path = sessions_base / f"{acc_id}{ext}"
        content = await session_file.read()
        dest_path.write_bytes(content)
        session_path = str(dest_path)
        await db.execute(
            "UPDATE telegram_accounts SET session_path = ? WHERE id = ?",
            (session_path, acc_id),
        )
        await db.commit()
    else:
        cursor = await db.execute(
            """INSERT INTO telegram_accounts (user_id, type, bot_token, status, name, created_at)
               VALUES (?, 'bot', ?, 'active', ?, ?)""",
            (user["id"], bot_token or "", name or "Bot account", now),
        )
        await db.commit()
        acc_id = cursor.lastrowid
    async with db.execute(
        "SELECT id, user_id, name, type, session_path, phone, status, created_at FROM telegram_accounts WHERE id = ?",
        (acc_id,),
    ) as cur:
        row = await cur.fetchone()
    return {
        "id": row[0],
        "user_id": row[1],
        "name": row[2],
        "type": row[3],
        "session_path": row[4],
        "phone": row[5],
        "status": row[6],
        "created_at": row[7],
    }


@router.patch("/{account_id}")
async def update_account(
    account_id: int,
    data: TelegramAccountUpdate,
    db: Db,
    user: CurrentUser,
) -> dict:
    """Update telegram account."""
    async with db.execute(
        "SELECT id, user_id FROM telegram_accounts WHERE id = ?",
        (account_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if user["role"] != "admin" and row[1] != user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    updates = []
    params = []
    if data.name is not None:
        updates.append("name = ?")
        params.append(data.name)
    if data.status is not None:
        updates.append("status = ?")
        params.append(data.status)
    if updates:
        params.append(account_id)
        await db.execute(f"UPDATE telegram_accounts SET {', '.join(updates)} WHERE id = ?", params)
        await db.commit()
    async with db.execute(
        "SELECT id, user_id, name, type, session_path, phone, status, created_at FROM telegram_accounts WHERE id = ?",
        (account_id,),
    ) as cur:
        row = await cur.fetchone()
    return {
        "id": row[0],
        "user_id": row[1],
        "name": row[2],
        "type": row[3],
        "session_path": row[4],
        "phone": row[5],
        "status": row[6],
        "created_at": row[7],
    }


@router.delete("/{account_id}")
async def delete_account(
    account_id: int,
    db: Db,
    user: CurrentUser,
) -> dict:
    """Delete telegram account and safely disable related mappings/workers."""
    async with db.execute(
        "SELECT id, user_id, session_path FROM telegram_accounts WHERE id = ?",
        (account_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if user["role"] != "admin" and row[1] != user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Disable mappings that use this account
    await db.execute(
        "UPDATE channel_mappings SET enabled = 0 WHERE telegram_account_id = ?",
        (account_id,),
    )

    # Stop any running workers for this account
    stop_workers_for_account(account_id)

    await db.execute("DELETE FROM telegram_accounts WHERE id = ?", (account_id,))
    await db.commit()

    if row[2]:
        try:
            Path(row[2]).unlink(missing_ok=True)
        except OSError:
            pass

    # Clean orphaned tmp_login_*.session files (from abandoned/failed phone logins)
    # Use project root from __file__ - Telethon creates tmp files there, not in cwd
    _project_root = Path(__file__).resolve().parents[4]  # routers -> web -> app -> src -> project
    for p in list(_project_root.glob("tmp_login_*.session")):
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass
    _sessions_dir = _project_root / settings.sessions_dir
    if _sessions_dir.exists():
        for p in list(_sessions_dir.rglob("tmp_login_*.session")):
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass

    return {"status": "ok"}
