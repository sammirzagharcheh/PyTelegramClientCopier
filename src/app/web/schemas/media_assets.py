"""Media asset schemas."""

from __future__ import annotations

from pydantic import BaseModel


class MediaAssetResponse(BaseModel):
    id: int
    user_id: int
    name: str
    file_path: str
    media_kind: str
    mime_type: str | None
    size_bytes: int | None
    created_at: str | None
