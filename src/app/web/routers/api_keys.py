"""User API keys (X-Api-Key authentication)."""

from __future__ import annotations

import hashlib
import secrets

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.auth.scopes import DEFAULT_API_KEY_SCOPES, validate_scopes_string
from app.web.deps import CurrentUser, Db, WriterUser
from app.web.scope_deps import resource_scope_dependency

router = APIRouter(
    prefix="/users",
    tags=["api-keys"],
    dependencies=[
        resource_scope_dependency("keys:read", "keys:write"),
    ],
)


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    scopes: str = DEFAULT_API_KEY_SCOPES

    @field_validator("scopes")
    @classmethod
    def _scopes_must_be_known(cls, v: str) -> str:
        try:
            return validate_scopes_string(v)
        except ValueError as e:
            raise ValueError(str(e)) from e


class ApiKeyCreatedResponse(BaseModel):
    id: int
    name: str
    scopes: str
    plain_key: str
    created_at: str | None


class ApiKeyListItem(BaseModel):
    id: int
    name: str
    scopes: str
    created_at: str | None
    last_used_at: str | None


@router.get("/me/api-keys", response_model=list[ApiKeyListItem])
async def list_api_keys(db: Db, user: CurrentUser) -> list[dict]:
    async with db.execute(
        "SELECT id, name, scopes, created_at, last_used_at FROM user_api_keys WHERE user_id = ? ORDER BY id",
        (user["id"],),
    ) as cur:
        rows = await cur.fetchall()
    return [
        {
            "id": r[0],
            "name": r[1],
            "scopes": r[2] or "",
            "created_at": r[3],
            "last_used_at": r[4],
        }
        for r in rows
    ]


@router.post("/me/api-keys", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(data: ApiKeyCreate, db: Db, user: WriterUser) -> dict:
    try:
        scopes = validate_scopes_string(data.scopes)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    plain = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(plain.encode("utf-8")).hexdigest()
    cur = await db.execute(
        "INSERT INTO user_api_keys (user_id, name, key_hash, scopes) VALUES (?, ?, ?, ?)",
        (user["id"], data.name.strip(), key_hash, scopes),
    )
    await db.commit()
    kid = cur.lastrowid
    async with db.execute(
        "SELECT id, name, scopes, created_at FROM user_api_keys WHERE id = ?",
        (kid,),
    ) as c2:
        row = await c2.fetchone()
    assert row
    return {
        "id": row[0],
        "name": row[1],
        "scopes": row[2] or "",
        "plain_key": plain,
        "created_at": row[3],
    }


@router.delete("/me/api-keys/{key_id}")
async def revoke_api_key(key_id: int, db: Db, user: WriterUser) -> dict:
    await db.execute(
        "DELETE FROM user_api_keys WHERE id = ? AND user_id = ?",
        (key_id, user["id"]),
    )
    await db.commit()
    return {"status": "ok"}
