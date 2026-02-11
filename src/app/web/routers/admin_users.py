"""Admin user management API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.password import hash_password
from app.web.deps import AdminUser, Db
from app.web.schemas.users import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


@router.get("", response_model=list[UserResponse])
async def list_users(
    db: Db,
    _admin: AdminUser,
    page: int = 1,
    page_size: int = 20,
    role: str | None = None,
    status_filter: str | None = None,
) -> list[dict]:
    """List users with optional filters."""
    offset = (page - 1) * page_size
    query = "SELECT id, email, name, role, status, created_at FROM users WHERE 1=1"
    params: list = []
    if role:
        query += " AND role = ?"
        params.append(role)
    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)
    query += " ORDER BY id LIMIT ? OFFSET ?"
    params.extend([page_size, offset])
    async with db.execute(query, params) as cur:
        rows = await cur.fetchall()
    return [
        {
            "id": r[0],
            "email": r[1],
            "name": r[2],
            "role": r[3],
            "status": r[4],
            "created_at": r[5],
        }
        for r in rows
    ]


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
