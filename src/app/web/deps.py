"""FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

import aiosqlite
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.jwt import decode_token
from app.db.sqlite import get_sqlite

bearer_scheme = HTTPBearer(auto_error=False)


async def get_db() -> aiosqlite.Connection:
    db = await get_sqlite()
    try:
        yield db
    finally:
        await db.close()


Db = Annotated[aiosqlite.Connection, Depends(get_db)]


async def get_current_user(
    db: Db,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
) -> dict:
    """Extract and validate JWT, return user dict from DB."""
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
        "SELECT id, email, name, role, status FROM users WHERE id = ? AND status = 'active'",
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
    }


CurrentUser = Annotated[dict, Depends(get_current_user)]


async def require_admin(user: CurrentUser) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


AdminUser = Annotated[dict, Depends(require_admin)]
