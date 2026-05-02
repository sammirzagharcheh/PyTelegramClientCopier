"""FastAPI dependencies."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.jwt import decode_token
from app.db.gateway import DbConnection, get_db_connection

bearer_scheme = HTTPBearer(auto_error=False)


async def get_db() -> DbConnection:
    db = await get_db_connection()
    try:
        yield db
    finally:
        await db.close()


Db = Annotated[DbConnection, Depends(get_db)]


async def get_current_user(
    db: Db,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
    x_api_key: Annotated[str | None, Header(alias="X-Api-Key")] = None,
) -> dict:
    """Extract and validate JWT or X-Api-Key, return user dict from DB."""
    if x_api_key and x_api_key.strip():
        key_hash = hashlib.sha256(x_api_key.strip().encode("utf-8")).hexdigest()
        async with db.execute(
            """SELECT u.id, u.email, u.name, u.role, u.status, u.timezone, ak.scopes
               FROM user_api_keys ak
               JOIN users u ON u.id = ak.user_id
               WHERE ak.key_hash = ? AND u.status = 'active'""",
            (key_hash,),
        ) as cur:
            row = await cur.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )
        now = datetime.now(timezone.utc)
        await db.execute(
            "UPDATE user_api_keys SET last_used_at = ? WHERE key_hash = ?",
            (now, key_hash),
        )
        await db.commit()
        scopes_raw = row[6] or ""
        scopes = [s.strip() for s in scopes_raw.split(",") if s.strip()]
        return {
            "id": row[0],
            "email": row[1],
            "name": row[2],
            "role": row[3],
            "status": row[4],
            "timezone": row[5] if len(row) > 5 else None,
            "api_key_scopes": scopes,
            "auth_via": "api_key",
        }

    tok = credentials.credentials if credentials is not None else None
    if not tok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    payload = decode_token(tok)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    async with db.execute(
        "SELECT id, email, name, role, status, timezone FROM users WHERE id = ? AND status = 'active'",
        (user_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return {
        "id": row[0],
        "email": row[1],
        "name": row[2],
        "role": row[3],
        "status": row[4],
        "timezone": row[5] if len(row) > 5 else None,
        "auth_via": "jwt",
    }


CurrentUser = Annotated[dict, Depends(get_current_user)]


async def require_writer(user: CurrentUser) -> dict:
    if user.get("role") == "viewer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Read-only accounts cannot modify data",
        )
    return user


WriterUser = Annotated[dict, Depends(require_writer)]


async def require_admin(user: CurrentUser) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


AdminUser = Annotated[dict, Depends(require_admin)]
