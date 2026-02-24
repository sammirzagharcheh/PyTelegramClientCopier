"""Shared mapping access control for mapping-scoped routes."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.web.deps import Db


async def get_mapping_scope(
    db: Db, user: dict, mapping_id: int
) -> tuple[int, int | None]:
    """
    Verify the current user has access to the mapping and return its scope.

    Returns (user_id, telegram_account_id). Raises 404 if mapping not found,
    403 if access denied (non-admin accessing another user's mapping).
    """
    async with db.execute(
        "SELECT user_id, telegram_account_id FROM channel_mappings WHERE id = ?",
        (mapping_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    if user["role"] != "admin" and row[0] != user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return int(row[0]), row[1]
