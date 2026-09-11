"""Admin invite management API."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field

from app.auth.invites import generate_invite_token, hash_invite_token, invite_is_expired
from app.web.deps import AdminUser, Db

router = APIRouter(prefix="/admin/invites", tags=["admin-invites"])

_ALLOWED_ROLES = frozenset({"admin", "user", "viewer"})


class InviteCreate(BaseModel):
    email: EmailStr
    role: str = "user"
    expires_in_hours: int = Field(default=72, ge=1, le=24 * 30)


class InviteCreatedResponse(BaseModel):
    id: int
    email: str
    role: str
    expires_at: str
    invite_path: str
    plain_token: str
    created_at: str | None


class InviteListItem(BaseModel):
    id: int
    email: str
    role: str
    expires_at: str
    used_at: str | None
    created_at: str | None
    created_by: int
    status: str  # pending | used | expired


def _status_for(expires_at: str, used_at: str | None) -> str:
    if used_at:
        return "used"
    if invite_is_expired(expires_at):
        return "expired"
    return "pending"


@router.get("", response_model=list[InviteListItem])
async def list_invites(
    db: Db,
    _admin: AdminUser,
    status_filter: str | None = Query(None, alias="status"),
) -> list[dict]:
    async with db.execute(
        """SELECT id, email, role, expires_at, used_at, created_at, created_by
           FROM admin_invites ORDER BY id DESC"""
    ) as cur:
        rows = await cur.fetchall()
    items = []
    for r in rows:
        st = _status_for(r[3], r[4])
        if status_filter and st != status_filter:
            continue
        items.append(
            {
                "id": r[0],
                "email": r[1],
                "role": r[2],
                "expires_at": r[3],
                "used_at": r[4],
                "created_at": r[5],
                "created_by": r[6],
                "status": st,
            }
        )
    return items


@router.post("", response_model=InviteCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(data: InviteCreate, db: Db, admin: AdminUser) -> dict:
    role = data.role.strip().lower()
    if role not in _ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="role must be one of: admin, user, viewer",
        )
    email = str(data.email).lower()
    async with db.execute("SELECT id FROM users WHERE email = ?", (email,)) as cur:
        if await cur.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

    plain = generate_invite_token()
    token_hash = hash_invite_token(plain)
    expires_at = (
        datetime.now(timezone.utc) + timedelta(hours=data.expires_in_hours)
    ).isoformat()
    cur = await db.execute(
        """INSERT INTO admin_invites (email, token_hash, role, created_by, expires_at)
           VALUES (?, ?, ?, ?, ?)""",
        (email, token_hash, role, admin["id"], expires_at),
    )
    await db.commit()
    invite_id = cur.lastrowid
    async with db.execute(
        "SELECT id, email, role, expires_at, created_at FROM admin_invites WHERE id = ?",
        (invite_id,),
    ) as c2:
        row = await c2.fetchone()
    assert row
    return {
        "id": row[0],
        "email": row[1],
        "role": row[2],
        "expires_at": row[3],
        "invite_path": f"/invite/{plain}",
        "plain_token": plain,
        "created_at": row[4],
    }


@router.delete("/{invite_id}")
async def revoke_invite(invite_id: int, db: Db, _admin: AdminUser) -> dict:
    async with db.execute(
        "SELECT id, used_at FROM admin_invites WHERE id = ?",
        (invite_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")
    if row[1]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invite already used",
        )
    await db.execute("DELETE FROM admin_invites WHERE id = ?", (invite_id,))
    await db.commit()
    return {"status": "ok"}
