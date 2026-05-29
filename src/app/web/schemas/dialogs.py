"""Telegram dialog list schemas."""

from __future__ import annotations

from pydantic import BaseModel


class TelegramDialogResponse(BaseModel):
    chat_id: int
    title: str
    username: str | None = None
    dialog_type: str


class TelegramDialogListResponse(BaseModel):
    items: list[TelegramDialogResponse]
