"""Telegram account Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel


class TelegramAccountCreate(BaseModel):
    name: str
    type: str  # 'user' or 'bot'
    session_path: str | None = None
    bot_token: str | None = None
    phone: str | None = None


class TelegramAccountUpdate(BaseModel):
    name: str | None = None
    status: str | None = None


class TelegramAccountResponse(BaseModel):
    id: int
    user_id: int
    name: str | None
    type: str
    session_path: str | None
    phone: str | None
    status: str
    created_at: str | None
