"""User-related Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None
    role: str = "user"


class UserUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    status: str | None = None
    password: str | None = None


class UserResponse(BaseModel):
    id: int
    email: str
    name: str | None
    role: str
    status: str
    created_at: str | None


class UserListParams(BaseModel):
    page: int = 1
    page_size: int = 20
    role: str | None = None
    status: str | None = None
    search: str | None = None
