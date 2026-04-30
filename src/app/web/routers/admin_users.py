"""Admin user management API routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.password import hash_password
from app.web.deps import AdminUser, Db
from app.web.schemas.users import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


_ALLOWED_SORT = {"id", "email", "name", "role", "status", "created_at"}


@router.get("")
async def list_users(
    db: Db,
    _admin: AdminUser,
    page: int = 1,
    page_size: int = 20,
    role: str | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    sort_by: str = "id",
    sort_order: str = "asc",
) -> dict:
    """List users with optional filters. Returns paginated {items, total, page, page_size, total_pages}."""
    page_size = min(max(1, page_size), 100)
    page = max(1, page)
    offset = (page - 1) * page_size
    col = sort_by if sort_by in _ALLOWED_SORT else "id"
    direction = "DESC" if sort_order.lower() == "desc" else "ASC"

    base = "FROM users WHERE 1=1"
    params: list = []
    if role:
        base += " AND role = ?"
        params.append(role)
    if status_filter:
        base += " AND status = ?"
        params.append(status_filter)
    if search:
        like = f"%{search.strip()}%"
        if like != "%%":
            base += " AND (LOWER(email) LIKE LOWER(?) OR LOWER(COALESCE(name, '')) LIKE LOWER(?))"
            params.extend([like, like])

    async with db.execute(f"SELECT COUNT(*) {base}", params) as cur:
        total = (await cur.fetchone())[0]

    query = f"SELECT id, email, name, role, status, created_at {base} ORDER BY {col} {direction} LIMIT ? OFFSET ?"
    params.extend([page_size, offset])
    async with db.execute(query, params) as cur:
        rows = await cur.fetchall()

    items = [
        {"id": r[0], "email": r[1], "name": r[2], "role": r[3], "status": r[4], "created_at": r[5]}
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


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate, db: Db, _admin: AdminUser) -> dict:
    """Create a new user."""
    if data.role not in ("admin", "user", "viewer"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="role must be one of: admin, user, viewer",
        )
    password_hash = hash_password(data.password)
    try:
        async with db.execute(
            """INSERT INTO users (email, password_hash, name, role, status)
               VALUES (?, ?, ?, ?, 'active')
               RETURNING id""",
            (data.email.lower(), password_hash, data.name or "", data.role),
        ) as cur:
            inserted = await cur.fetchone()
        await db.commit()
        if not inserted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user",
            )
        uid = int(inserted[0])
    except Exception as e:
        if "UNIQUE" in str(e) or "unique" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            ) from e
        raise
    async with db.execute(
        "SELECT id, email, name, role, status, created_at FROM users WHERE id = ?",
        (uid,),
    ) as cur:
        row = await cur.fetchone()
    return {
        "id": row[0],
        "email": row[1],
        "name": row[2],
        "role": row[3],
        "status": row[4],
        "created_at": row[5],
    }


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Db, _admin: AdminUser) -> dict:
    """Get user by ID."""
    async with db.execute(
        "SELECT id, email, name, role, status, created_at FROM users WHERE id = ?",
        (user_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {
        "id": row[0],
        "email": row[1],
        "name": row[2],
        "role": row[3],
        "status": row[4],
        "created_at": row[5],
    }


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int, data: UserUpdate, db: Db, _admin: AdminUser
) -> dict:
    """Update user."""
    updates: list[str] = []
    params: list = []
    if data.name is not None:
        updates.append("name = ?")
        params.append(data.name)
    if data.role is not None:
        if data.role not in ("admin", "user", "viewer"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="role must be one of: admin, user, viewer",
            )
        updates.append("role = ?")
        params.append(data.role)
    if data.status is not None:
        if data.status not in ("active", "inactive"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="status must be one of: active, inactive",
            )
        updates.append("status = ?")
        params.append(data.status)
    if data.password is not None:
        updates.append("password_hash = ?")
        params.append(hash_password(data.password))
    if updates:
        params.append(user_id)
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            f"UPDATE users SET {', '.join(updates)}, updated_at = ? WHERE id = ?",
            [*params[:-1], now, params[-1]],
        )
        await db.commit()
    async with db.execute(
        "SELECT id, email, name, role, status, created_at FROM users WHERE id = ?",
        (user_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {
        "id": row[0],
        "email": row[1],
        "name": row[2],
        "role": row[3],
        "status": row[4],
        "created_at": row[5],
    }


@router.delete("/{user_id}")
async def delete_user(user_id: int, db: Db, admin: AdminUser) -> dict:
    """Delete user and related data."""
    if user_id == admin["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account",
        )

    async with db.execute(
        "SELECT id, email, role, status FROM users WHERE id = ?",
        (user_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Clean up mapping-dependent rows first, then user-owned rows, then the user row.
    await db.execute(
        "DELETE FROM mapping_filters WHERE mapping_id IN (SELECT id FROM channel_mappings WHERE user_id = ?)",
        (user_id,),
    )
    await db.execute(
        "DELETE FROM mapping_schedules WHERE mapping_id IN (SELECT id FROM channel_mappings WHERE user_id = ?)",
        (user_id,),
    )
    await db.execute(
        "DELETE FROM mapping_transform_rules WHERE mapping_id IN (SELECT id FROM channel_mappings WHERE user_id = ?)",
        (user_id,),
    )
    await db.execute("DELETE FROM channel_mappings WHERE user_id = ?", (user_id,))
    await db.execute("DELETE FROM telegram_accounts WHERE user_id = ?", (user_id,))
    await db.execute("DELETE FROM refresh_tokens WHERE user_id = ?", (user_id,))
    await db.execute("DELETE FROM login_sessions WHERE user_id = ?", (user_id,))
    await db.execute("DELETE FROM worker_registry WHERE user_id = ?", (user_id,))
    await db.execute("DELETE FROM user_schedules WHERE user_id = ?", (user_id,))
    await db.execute("DELETE FROM media_assets WHERE user_id = ?", (user_id,))
    await db.execute("DELETE FROM user_alert_webhooks WHERE user_id = ?", (user_id,))
    await db.execute("DELETE FROM user_api_keys WHERE user_id = ?", (user_id,))
    await db.execute("DELETE FROM dest_message_index WHERE user_id = ?", (user_id,))
    await db.execute("DELETE FROM admin_invites WHERE created_by = ?", (user_id,))
    await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    await db.commit()
    return {"status": "ok"}
