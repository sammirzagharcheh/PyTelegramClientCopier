from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from telethon import TelegramClient
from telethon.errors import (
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
)

from app.config import settings
from app.web.deps import CurrentUser, Db


router = APIRouter(prefix="/accounts/login", tags=["accounts-login"])


class BeginLoginRequest(BaseModel):
    phone: str


class BeginLoginResponse(BaseModel):
    login_session_id: int


class CompleteLoginRequest(BaseModel):
    login_session_id: int
    code: str
    password: str | None = None
    account_name: str | None = None


class CancelLoginRequest(BaseModel):
    login_session_id: int


@router.post("/begin", response_model=BeginLoginResponse)
async def begin_login(data: BeginLoginRequest, user: CurrentUser, db: Db) -> dict:
    """Begin Telethon phone login for a user account."""
    phone = data.phone.strip()
    if not phone.startswith("+") or len(phone) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone must start with + and be a valid international number.",
        )

    if settings.api_id is None or settings.api_hash is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API_ID and API_HASH must be configured.",
        )

    tmp_session_name = f"tmp_login_{uuid.uuid4().hex}"

    client = TelegramClient(tmp_session_name, settings.api_id, settings.api_hash)
    await client.connect()
    try:
        sent = await client.send_code_request(phone)
        phone_code_hash = getattr(sent, "phone_code_hash", None)

        # #region agent log
        try:
            from pathlib import Path as _DbgPath
            import time as _dbg_time

            dbg_entry = {
                "id": f"log_begin_{_dbg_time.time()}",
                "timestamp": int(_dbg_time.time() * 1000),
                "location": "accounts_login.py:begin_login",
                "message": "begin_login_tmp",
                "data": {
                    "user_id": user["id"],
                    "tmp_session_name": tmp_session_name,
                    "cwd": str(_DbgPath(".").resolve()),
                    "tmp_exists": _DbgPath(f"{tmp_session_name}.session").exists(),
                },
                "runId": "pre-fix",
                "hypothesisId": "H3",
            }
            dbg_log_path = _DbgPath(
                r"d:\Ongoing Projects\TelegramClientCopier\.cursor\debug.log"
            )
            dbg_log_path.parent.mkdir(parents=True, exist_ok=True)
            with dbg_log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(dbg_entry) + "\n")
        except Exception:
            pass
        # #endregion agent log

    except Exception as e:  # Telethon error
        await client.disconnect()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to send code: {e}",
        ) from e

    cursor = await db.execute(
        """
        INSERT INTO login_sessions (user_id, phone, tmp_session_name, status, phone_code_hash)
        VALUES (?, ?, ?, 'pending', ?)
        """,
        (user["id"], phone, tmp_session_name, phone_code_hash),
    )
    await db.commit()
    login_session_id = cursor.lastrowid

    await client.disconnect()

    return {"login_session_id": login_session_id}


@router.post("/complete")
async def complete_login(data: CompleteLoginRequest, user: CurrentUser, db: Db) -> dict:
    """Complete Telethon phone login, persist session, and create telegram_accounts row."""
    async with db.execute(
        "SELECT id, user_id, phone, tmp_session_name, status, phone_code_hash "
        "FROM login_sessions WHERE id = ?",
        (data.login_session_id,),
    ) as cur:
        row = await cur.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Login session not found."
        )

    login_id, login_user_id, phone, tmp_session_name, status_val, phone_code_hash = row

    if status_val != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Login session is not pending.",
        )

    if user["role"] != "admin" and login_user_id != user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied."
        )

    if settings.api_id is None or settings.api_hash is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API_ID and API_HASH must be configured.",
        )

    if not phone_code_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending login code found. Please start login again.",
        )

    client = TelegramClient(tmp_session_name, settings.api_id, settings.api_hash)
    await client.connect()
    try:
        try:
            await client.sign_in(
                phone=phone,
                code=data.code,
                phone_code_hash=phone_code_hash,
                password=data.password or None,
            )
        except SessionPasswordNeededError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "2FA password required",
                    "code": "2FA_REQUIRED",
                },
            )
        except PhoneCodeExpiredError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Code expired. Please restart login.",
            )
        except PhoneCodeInvalidError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid code.",
            )
        except Exception as e:
            # #region agent log
            try:
                log_entry = {
                    "id": f"log_complete_{datetime.now(timezone.utc).timestamp()}",
                    "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
                    "location": "accounts_login.py:complete_login",
                    "message": "telethon_sign_in_error",
                    "data": {
                        "login_session_id": data.login_session_id,
                        "error_type": type(e).__name__,
                        "error_str": str(e),
                    },
                    "runId": "pre-fix",
                    "hypothesisId": "telethon-sign-in",
                }
                log_path = Path(
                    r"d:\Ongoing Projects\TelegramClientCopier\.cursor\debug.log"
                )
                log_path.parent.mkdir(parents=True, exist_ok=True)
                with log_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry) + "\n")
            except Exception:
                pass
            # #endregion agent log
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Login failed: {e}",
            ) from e

        # At this point we've successfully signed in; disconnect the client so
        # Telethon releases any file handles on the temporary session file
        await client.disconnect()

        now = datetime.now(timezone.utc).isoformat()
        account_name = data.account_name or "User account"

        cursor = await db.execute(
            """
            INSERT INTO telegram_accounts (user_id, type, status, name, created_at)
            VALUES (?, 'user', 'active', ?, ?)
            """,
            (login_user_id, account_name, now),
        )
        await db.commit()
        account_id = cursor.lastrowid

        sessions_base = Path(settings.sessions_dir) / str(login_user_id)
        sessions_base.mkdir(parents=True, exist_ok=True)

        tmp_file = Path(f"{tmp_session_name}.session")
        final_path = sessions_base / f"{account_id}.session"

        if not tmp_file.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Temporary session file not found.",
            )

        tmp_file.replace(final_path)

        await db.execute(
            "UPDATE telegram_accounts SET session_path = ? WHERE id = ?",
            (str(final_path), account_id),
        )
        await db.execute(
            "UPDATE login_sessions SET status = 'completed' WHERE id = ?",
            (login_id,),
        )
        await db.commit()

        async with db.execute(
            "SELECT id, user_id, name, type, session_path, phone, status, created_at "
            "FROM telegram_accounts WHERE id = ?",
            (account_id,),
        ) as cur:
            acc_row = await cur.fetchone()

        return {
            "id": acc_row[0],
            "user_id": acc_row[1],
            "name": acc_row[2],
            "type": acc_row[3],
            "session_path": acc_row[4],
            "phone": acc_row[5],
            "status": acc_row[6],
            "created_at": acc_row[7],
        }
    finally:
        # Best-effort disconnect; ignore if already closed
        try:
            await client.disconnect()
        except Exception:
            pass


@router.post("/cancel")
async def cancel_login(
    data: CancelLoginRequest,
    user: CurrentUser,
    db: Db,
) -> dict:
    """Cancel an in-progress login and clean up temporary session file."""
    async with db.execute(
        "SELECT id, user_id, tmp_session_name, status FROM login_sessions WHERE id = ?",
        (data.login_session_id,),
    ) as cur:
        row = await cur.fetchone()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Login session not found.")

    login_id, login_user_id, tmp_session_name, status_val = row

    if status_val != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Login session is not pending.")

    if user["role"] != "admin" and login_user_id != user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    await db.execute(
        "UPDATE login_sessions SET status = 'cancelled' WHERE id = ?",
        (login_id,),
    )
    await db.commit()

    tmp_file = Path(f"{tmp_session_name}.session")
    if tmp_file.exists():
        try:
            tmp_file.unlink()
        except OSError:
            # best-effort cleanup
            pass

    return {"status": "ok"}

