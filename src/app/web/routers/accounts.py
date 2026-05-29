"""Telegram accounts API routes."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi import status as http_status

from app.config import settings
from app.telegram.dialog_service import (
    AccountCredentials,
    SessionLockedError,
    TelegramDialogsError,
    list_account_dialogs,
)
from app.web.schemas.accounts import TelegramAccountUpdate
from app.web.schemas.dialogs import TelegramDialogListResponse, TelegramDialogResponse
from app.web.deps import AdminUser, CurrentUser, Db, WriterUser
from app.web.routers.workers import stop_workers_for_account

router = APIRouter(prefix="/accounts", tags=["accounts"])


_ALLOWED_SORT = {"id", "name", "type", "status", "created_at", "user_id"}


@router.get("")
async def list_accounts(
    db: Db,
    user: CurrentUser,
    user_id: int | None = None,
    account_status: str | None = Query(None, alias="status"),
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "id",
    sort_order: str = "asc",
) -> dict:
    """List telegram accounts. Users see own; admins can filter by user_id. Returns paginated {items, total, page, page_size, total_pages}."""
    page_size = min(max(1, page_size), 100)
    page = max(1, page)
    offset = (page - 1) * page_size
    col = sort_by if sort_by in _ALLOWED_SORT else "id"
    direction = "DESC" if sort_order.lower() == "desc" else "ASC"
    order = f"ORDER BY {col} {direction}"

    status_filter = ""
    status_params: list = []
    if account_status is not None:
        normalized = account_status.strip().lower()
        if normalized not in ("active", "inactive"):
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="status must be 'active' or 'inactive'",
            )
        status_filter = " AND status = ?"
        status_params = [normalized]

    if user["role"] == "admin":
        if user_id is not None:
            scope_id = user_id
        else:
            scope_id = -1
        if scope_id == -1:
            base = f"FROM telegram_accounts WHERE 1=1{status_filter}"
            params: list = list(status_params)
        else:
            base = f"FROM telegram_accounts WHERE user_id = ?{status_filter}"
            params = [scope_id, *status_params]
    else:
        base = f"FROM telegram_accounts WHERE user_id = ?{status_filter}"
        params = [user["id"], *status_params]

    async with db.execute(f"SELECT COUNT(*) {base}", params) as cur:
        total = (await cur.fetchone())[0]

    params.extend([page_size, offset])
    async with db.execute(
        f"SELECT id, user_id, name, type, session_path, phone, status, created_at {base} {order} LIMIT ? OFFSET ?",
        params,
    ) as cur:
        rows = await cur.fetchall()

    items = [
        {"id": r[0], "user_id": r[1], "name": r[2], "type": r[3], "session_path": r[4], "phone": r[5], "status": r[6], "created_at": r[7]}
        for r in rows
    ]
    total_pages = max(1, (total + page_size - 1) // page_size) if total else 1
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


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
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Account not found")
    if user["role"] != "admin" and row[1] != user["id"]:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Access denied")
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


async def _fetch_account_credentials(db: Db, account_id: int) -> tuple | None:
    async with db.execute(
        "SELECT id, user_id, type, session_path, bot_token, status FROM telegram_accounts WHERE id = ?",
        (account_id,),
    ) as cur:
        return await cur.fetchone()


@router.get("/{account_id}/dialogs", response_model=TelegramDialogListResponse)
async def list_account_dialogs_route(
    account_id: int,
    db: Db,
    user: CurrentUser,
    limit: int = 500,
) -> dict:
    """List Telegram chats/channels for an active account."""
    row = await _fetch_account_credentials(db, account_id)
    if not row:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Account not found")
    if user["role"] != "admin" and row[1] != user["id"]:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Access denied")
    if row[5] != "active":
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Account must be active to list chats",
        )
    acc_type = row[2]
    session_path = row[3]
    bot_token = row[4]
    if acc_type == "user" and not session_path:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Account is not connected",
        )
    if acc_type == "bot" and not bot_token:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Account is not connected",
        )

    account = AccountCredentials(
        account_id=row[0],
        user_id=row[1],
        account_type=acc_type,
        session_path=session_path,
        bot_token=bot_token,
        status=row[5],
    )
    try:
        dialogs = await list_account_dialogs(account, limit=limit)
    except SessionLockedError:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="Account session is in use; stop the worker and retry",
        ) from None
    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except TelegramDialogsError:
        raise HTTPException(
            status_code=http_status.HTTP_502_BAD_GATEWAY,
            detail="Could not load chats from Telegram",
        ) from None

    return {
        "items": [
            TelegramDialogResponse(
                chat_id=d.chat_id,
                title=d.title,
                username=d.username,
                dialog_type=d.dialog_type,
            ).model_dump()
            for d in dialogs
        ],
    }


@router.post("", status_code=http_status.HTTP_201_CREATED)
async def create_account(
    db: Db,
    user: WriterUser,
    name: str = Form(...),
    type: str = Form(...),
    bot_token: str | None = Form(None),
    session_file: UploadFile | None = File(None),
) -> dict:
    """Create telegram account. For type=user, upload session file. For type=bot, provide bot_token."""
    if type not in ("user", "bot"):
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="type must be 'user' or 'bot'")
    if type == "bot" and not bot_token:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="bot_token required for bot accounts")
    if type == "user" and not session_file:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="session_file required for user accounts")
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
    user: WriterUser,
) -> dict:
    """Update telegram account."""
    async with db.execute(
        "SELECT id, user_id FROM telegram_accounts WHERE id = ?",
        (account_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Account not found")
    if user["role"] != "admin" and row[1] != user["id"]:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Access denied")
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
    user: WriterUser,
) -> dict:
    """Delete telegram account and safely disable related mappings/workers."""
    async with db.execute(
        "SELECT id, user_id, session_path FROM telegram_accounts WHERE id = ?",
        (account_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Account not found")
    if user["role"] != "admin" and row[1] != user["id"]:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Disable mappings that use this account
    await db.execute(
        "UPDATE channel_mappings SET enabled = 0 WHERE telegram_account_id = ?",
        (account_id,),
    )

    # Stop any running workers for this account
    await stop_workers_for_account(account_id, db)

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
