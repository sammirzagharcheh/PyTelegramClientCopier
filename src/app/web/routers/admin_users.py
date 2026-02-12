"""Admin user management API routes."""

from __future__ import annotations

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
    password_hash = hash_password(data.password)
    try:
        cursor = await db.execute(
            """INSERT INTO users (email, password_hash, name, role, status)
               VALUES (?, ?, ?, ?, 'active')""",
            (data.email.lower(), password_hash, data.name or "", data.role),
        )
        await db.commit()
        uid = cursor.lastrowid
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
        updates.append("role = ?")
        params.append(data.role)
    if data.status is not None:
        updates.append("status = ?")
        params.append(data.status)
    if data.password is not None:
        updates.append("password_hash = ?")
        params.append(hash_password(data.password))
    if updates:
        params.append(user_id)
        await db.execute(
            f"UPDATE users SET {', '.join(updates)}, updated_at = datetime('now') WHERE id = ?",
            params,
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
