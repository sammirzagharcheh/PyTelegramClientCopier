"""Media asset routes (upload/list/delete) for transform-based media replacement."""

from __future__ import annotations

import logging
import mimetypes
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.config import project_root, settings
from app.web.deps import CurrentUser, Db
from app.web.schemas.media_assets import MediaAssetResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/media-assets", tags=["media-assets"])

_ALLOWED_MEDIA_KINDS = {"photo", "video", "voice", "other"}
# 50 MB upload limit
_MAX_UPLOAD_BYTES = 50 * 1024 * 1024
# Characters that are invalid or problematic on common filesystems
_UNSAFE_FILENAME_RE = re.compile(r'[^\w.\-]')


def _sanitize_filename(raw: str) -> str:
    """Replace unsafe filesystem characters with underscores, preserving extension."""
    return _UNSAFE_FILENAME_RE.sub("_", raw)


def _infer_media_kind(content_type: str | None, filename: str | None) -> str:
    ctype = (content_type or "").lower()
    if ctype.startswith("image/"):
        return "photo"
    if ctype.startswith("video/"):
        return "video"
    if ctype.startswith("audio/"):
        return "voice"
    guessed, _ = mimetypes.guess_type(filename or "")
    if guessed:
        g = guessed.lower()
        if g.startswith("image/"):
            return "photo"
        if g.startswith("video/"):
            return "video"
        if g.startswith("audio/"):
            return "voice"
    return "other"


def _normalize_media_kind(value: str | None, content_type: str | None, filename: str | None) -> str:
    if value is None or value.strip() == "":
        return _infer_media_kind(content_type, filename)
    kind = value.strip().lower()
    if kind not in _ALLOWED_MEDIA_KINDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="media_kind must be one of: photo, video, voice, other",
        )
    return kind


def _asset_row_to_dict(row: tuple) -> dict:
    return {
        "id": row[0],
        "user_id": row[1],
        "name": row[2],
        "file_path": row[3],
        "media_kind": row[4],
        "mime_type": row[5],
        "size_bytes": row[6],
        "created_at": row[7],
    }


@router.get("", response_model=list[MediaAssetResponse])
async def list_media_assets(db: Db, user: CurrentUser, user_id: int | None = None) -> list[dict]:
    """List uploaded media assets. Users see own assets; admins can optionally filter by user_id."""
    if user["role"] == "admin":
        if user_id is None:
            async with db.execute(
                "SELECT id, user_id, name, file_path, media_kind, mime_type, size_bytes, created_at "
                "FROM media_assets ORDER BY id DESC"
            ) as cur:
                rows = await cur.fetchall()
        else:
            async with db.execute(
                "SELECT id, user_id, name, file_path, media_kind, mime_type, size_bytes, created_at "
                "FROM media_assets WHERE user_id = ? ORDER BY id DESC",
                (user_id,),
            ) as cur:
                rows = await cur.fetchall()
    else:
        async with db.execute(
            "SELECT id, user_id, name, file_path, media_kind, mime_type, size_bytes, created_at "
            "FROM media_assets WHERE user_id = ? ORDER BY id DESC",
            (user["id"],),
        ) as cur:
            rows = await cur.fetchall()
    return [_asset_row_to_dict(r) for r in rows]


@router.post("", response_model=MediaAssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_media_asset(
    db: Db,
    user: CurrentUser,
    file: UploadFile = File(...),
    name: str | None = Form(None),
    media_kind: str | None = Form(None),
) -> dict:
    """Upload a media asset for replacement rules."""
    safe_filename = _sanitize_filename(Path(file.filename or "").name or "asset.bin")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB",
        )

    kind = _normalize_media_kind(media_kind, file.content_type, safe_filename)
    now = datetime.now(timezone.utc).isoformat()

    root = project_root()
    assets_root = root / settings.media_assets_dir / str(user["id"])
    assets_root.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}_{safe_filename}"
    dest = assets_root / stored_name
    dest.write_bytes(data)

    # Store the path relative to the project root for portability across deployments.
    relative_path = str(dest.relative_to(root))
    display_name = (name or safe_filename).strip() or safe_filename
    cursor = await db.execute(
        "INSERT INTO media_assets (user_id, name, file_path, media_kind, mime_type, size_bytes, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user["id"], display_name, relative_path, kind, file.content_type, len(data), now),
    )
    await db.commit()

    asset_id = cursor.lastrowid
    async with db.execute(
        "SELECT id, user_id, name, file_path, media_kind, mime_type, size_bytes, created_at "
        "FROM media_assets WHERE id = ?",
        (asset_id,),
    ) as cur:
        row = await cur.fetchone()
    return _asset_row_to_dict(row)


@router.delete("/{asset_id}")
async def delete_media_asset(asset_id: int, db: Db, user: CurrentUser) -> dict:
    """Delete a media asset if unused by transform rules."""
    async with db.execute(
        "SELECT id, user_id, file_path FROM media_assets WHERE id = ?",
        (asset_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset not found")
    if user["role"] != "admin" and row[1] != user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Atomically delete only if the asset is not referenced by any transform rules,
    # preventing a TOCTOU race between the usage check and the DELETE.
    cursor = await db.execute(
        """
        DELETE FROM media_assets
        WHERE id = ?
          AND NOT EXISTS (
              SELECT 1 FROM mapping_transform_rules
              WHERE replacement_media_asset_id = ?
          )
        """,
        (asset_id, asset_id),
    )
    await db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Media asset is in use by transform rules",
        )

    stored_path = row[2]
    # Resolve relative paths against the project root; absolute paths are used as-is
    # (backward compat with pre-migration entries that stored absolute paths).
    file_path = Path(stored_path) if Path(stored_path).is_absolute() else project_root() / stored_path
    try:
        file_path.unlink(missing_ok=True)
    except OSError as exc:
        logger.warning("Failed to delete media asset file %r: %s", str(file_path), exc)
    return {"status": "ok"}
