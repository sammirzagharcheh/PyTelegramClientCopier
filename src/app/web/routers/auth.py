"""Auth API routes."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import create_access_token, create_refresh_token, decode_token
from app.auth.password import hash_password, verify_password
from app.web.deps import CurrentUser, Db
from app.web.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    UpdateProfileRequest,
    UserMe,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest, db: Db) -> dict:
    """Login with email and password, returns access and refresh tokens."""
    async with db.execute(
        "SELECT id, email, name, role, status, password_hash FROM users WHERE email = ?",
        (data.email.lower(),),
    ) as cur:
        row = await cur.fetchone()
    if not row or row[5] is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    user_id, email, name, role, user_status, password_hash = row
    if user_status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is not active",
        )
    if not verify_password(data.password, password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    access_token = create_access_token(sub=email, user_id=user_id, role=role)
    refresh_token = create_refresh_token(sub=email, user_id=user_id)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await db.execute(
        "INSERT INTO refresh_tokens (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
        (user_id, _hash_token(refresh_token), expires_at.isoformat()),
    )
    await db.commit()
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(data: RefreshRequest, db: Db) -> dict:
    """Exchange refresh token for new access token."""
    payload = decode_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    token_hash = _hash_token(data.refresh_token)
    async with db.execute(
        "SELECT id FROM refresh_tokens WHERE user_id = ? AND token_hash = ? AND expires_at > datetime('now')",
        (user_id, token_hash),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired or invalid",
        )
    async with db.execute(
        "SELECT id, email, name, role FROM users WHERE id = ? AND status = 'active'",
        (user_id,),
    ) as cur:
        user_row = await cur.fetchone()
    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    access_token = create_access_token(
        sub=user_row[1], user_id=user_row[0], role=user_row[3]
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(data: RefreshRequest, db: Db) -> dict:
    """Invalidate refresh token (client should discard tokens)."""
    token_hash = _hash_token(data.refresh_token)
    await db.execute(
        "DELETE FROM refresh_tokens WHERE token_hash = ?", (token_hash,)
    )
    await db.commit()
    return {"status": "ok"}


@router.get("/me", response_model=UserMe)
async def me(user: CurrentUser) -> dict:
    """Get current user profile."""
    return user


@router.patch("/me", response_model=UserMe)
async def update_me(
    data: UpdateProfileRequest,
    user: CurrentUser,
    db: Db,
) -> dict:
    """Update current user profile (e.g. timezone preference)."""
    if data.timezone is not None:
        try:
            ZoneInfo(data.timezone)
        except ZoneInfoNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid timezone",
            )
        await db.execute(
            "UPDATE users SET timezone = ? WHERE id = ?",
            (data.timezone, user["id"]),
        )
    else:
        await db.execute(
            "UPDATE users SET timezone = NULL WHERE id = ?",
            (user["id"],),
        )
    await db.commit()
    async with db.execute(
        "SELECT id, email, name, role, status, timezone FROM users WHERE id = ? AND status = 'active'",
        (user["id"],),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User not found")
    return {
        "id": row[0],
        "email": row[1],
        "name": row[2],
        "role": row[3],
        "status": row[4],
        "timezone": row[5] if len(row) > 5 else None,
    }


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    user: CurrentUser,
    db: Db,
) -> dict:
    """Change current user's password. Requires current password verification."""
    async with db.execute(
        "SELECT password_hash FROM users WHERE id = ?",
        (user["id"],),
    ) as cur:
        row = await cur.fetchone()
    if not row or row[0] is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password change not supported for this account",
        )
    if not verify_password(data.current_password, row[0]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    new_hash = hash_password(data.new_password)
    await db.execute(
        "UPDATE users SET password_hash = ?, updated_at = datetime('now') WHERE id = ?",
        (new_hash, user["id"]),
    )
    await db.commit()
    return {"status": "ok"}
