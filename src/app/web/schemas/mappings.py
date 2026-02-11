"""Channel mapping Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel


class MappingFilterCreate(BaseModel):
    include_text: str | None = None
    exclude_text: str | None = None
    media_types: str | None = None
    regex_pattern: str | None = None


class MappingFilterUpdate(BaseModel):
    include_text: str | None = None
    exclude_text: str | None = None
    media_types: str | None = None
    regex_pattern: str | None = None


class MappingFilterResponse(BaseModel):
    id: int
    mapping_id: int
    include_text: str | None
    exclude_text: str | None
    media_types: str | None
    regex_pattern: str | None


class ChannelMappingCreate(BaseModel):
    source_chat_id: int
    dest_chat_id: int
    name: str | None = None
    telegram_account_id: int | None = None
    source_chat_title: str | None = None
    dest_chat_title: str | None = None


class ChannelMappingUpdate(BaseModel):
    name: str | None = None
    source_chat_id: int | None = None
    dest_chat_id: int | None = None
    enabled: bool | None = None
    source_chat_title: str | None = None
    dest_chat_title: str | None = None


class ChannelMappingResponse(BaseModel):
    id: int
    user_id: int
    source_chat_id: int
    dest_chat_id: int
    name: str | None
    source_chat_title: str | None
    dest_chat_title: str | None
    enabled: bool
    telegram_account_id: int | None
    created_at: str | None
