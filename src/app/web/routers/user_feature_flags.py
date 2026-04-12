"""Per-user feature flags (JSON blob in app_settings)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.feature_flags import get_user_feature_flags, set_user_feature_flags
from app.web.deps import CurrentUser, Db, WriterUser

router = APIRouter(prefix="/users", tags=["feature-flags"])


class FeatureFlagsUpdate(BaseModel):
    flags: dict[str, Any]


@router.get("/me/feature-flags")
async def get_flags(db: Db, user: CurrentUser) -> dict[str, Any]:
    return await get_user_feature_flags(db, int(user["id"]))


@router.patch("/me/feature-flags")
async def patch_flags(
    data: FeatureFlagsUpdate,
    db: Db,
    user: WriterUser,
) -> dict[str, Any]:
    current = await get_user_feature_flags(db, int(user["id"]))
    current.update(data.flags)
    await set_user_feature_flags(db, int(user["id"]), current)
    return current
