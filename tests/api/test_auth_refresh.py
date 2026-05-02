"""API tests for POST /auth/refresh token flow."""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timedelta, timezone

from app.auth import create_refresh_token
from app.db.gateway import get_db_connection


def test_refresh_rejects_db_expired_token_without_500(api_client):
    """Expired refresh row should return 401 (never 500 type/cast errors)."""
    login_r = api_client.post(
        "/api/auth/login",
        json={"email": "user@test.com", "password": "pass"},
    )
    assert login_r.status_code == 200
    refresh_token = login_r.json()["refresh_token"]

    async def expire_row() -> None:
        db = await get_db_connection()
        try:
            expired_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            await db.execute(
                "UPDATE refresh_tokens SET expires_at = ? WHERE token_hash = ?",
                (expired_at.isoformat(), hashlib.sha256(refresh_token.encode()).hexdigest()),
            )
            await db.commit()
        finally:
            await db.close()

    asyncio.run(expire_row())

    refresh_r = api_client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_r.status_code == 401
    assert "expired or invalid" in refresh_r.json().get("detail", "").lower()


def test_refresh_with_valid_token_returns_access_token(api_client):
    """Valid refresh token returns a fresh access token."""
    refresh_token = create_refresh_token(sub="user@test.com", user_id=1)
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

    async def seed_valid_row() -> None:
        db = await get_db_connection()
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(days=2)
            created_at = datetime.now(timezone.utc)
            await db.execute(
                "INSERT INTO refresh_tokens (user_id, token_hash, expires_at, created_at) VALUES (?, ?, ?, ?)",
                (1, token_hash, expires_at.isoformat(), created_at.isoformat()),
            )
            await db.commit()
        finally:
            await db.close()

    asyncio.run(seed_valid_row())

    refresh_r = api_client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_r.status_code == 200
    body = refresh_r.json()
    assert body.get("token_type") == "bearer"
    assert isinstance(body.get("access_token"), str) and body["access_token"]
