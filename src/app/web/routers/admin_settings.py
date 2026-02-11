"""Admin settings API - MongoDB URI, etc."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.config import settings
from app.services.app_settings import get_setting, mask_mongo_uri, set_setting
from app.web.deps import AdminUser, Db

router = APIRouter(prefix="/admin/settings", tags=["admin-settings"])

MONGO_URI_PATTERN = re.compile(r"^mongodb(\+srv)?://.+$")


class SettingsUpdate(BaseModel):
    mongo_uri: str | None = None
    mongo_db: str | None = None


async def _get_settings_dict(db: Db) -> dict:
    mongo_uri = await get_setting(db, "mongo_uri")
    mongo_db = await get_setting(db, "mongo_db")
    return {
        "mongo_uri": mask_mongo_uri(mongo_uri or settings.mongo_uri),
        "mongo_uri_set": bool(mongo_uri),
        "mongo_db": mongo_db or settings.mongo_db,
        "mongo_db_set": bool(mongo_db),
    }


@router.get("")
async def get_settings(db: Db, _admin: AdminUser) -> dict:
    """Get app settings (MongoDB URI is masked)."""
    return await _get_settings_dict(db)


@router.patch("")
async def update_settings(
    db: Db,
    _admin: AdminUser,
    data: SettingsUpdate,
) -> dict:
    """Update app settings. Pass only fields to change."""
    if data.mongo_uri is not None:
        val = data.mongo_uri.strip() or None
        if val and not MONGO_URI_PATTERN.match(val):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="mongo_uri must be a valid MongoDB connection string (mongodb:// or mongodb+srv://)",
            )
        await set_setting(db, "mongo_uri", val)
    if data.mongo_db is not None:
        val = data.mongo_db.strip() or None
        if val and not all(c.isalnum() or c in "_-" for c in val):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="mongo_db must be alphanumeric (with - or _ allowed)",
            )
        await set_setting(db, "mongo_db", val)
    return await _get_settings_dict(db)


@router.post("/test-mongo")
async def test_mongo_connection(db: Db, _admin: AdminUser) -> dict:
    """Test the current MongoDB connection."""
    from app.db.mongo import get_mongo_db

    try:
        mongo_db = get_mongo_db()
        await mongo_db.command("ping")
        return {"status": "ok", "message": "Connected successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MongoDB connection failed: {str(e)}",
        )
