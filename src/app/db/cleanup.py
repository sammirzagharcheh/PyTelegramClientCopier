"""Database cleanup tasks."""

from __future__ import annotations

import logging

import aiosqlite

from app.config import settings

logger = logging.getLogger(__name__)


async def purge_old_login_sessions(retention_days: int) -> int:
    """
    Delete completed/cancelled login_sessions older than retention_days.
    Pending sessions are never deleted.
    Returns number of rows deleted.
    """
    deleted = 0
    try:
        async with aiosqlite.connect(settings.sqlite_path) as db:
            cursor = await db.execute(
                """
                DELETE FROM login_sessions
                WHERE status IN ('completed', 'cancelled')
                AND created_at < datetime('now', '-' || ? || ' days')
                """,
                (retention_days,),
            )
            await db.commit()
            deleted = cursor.rowcount
        if deleted:
            logger.info("Purged %d old login_sessions rows (retention=%d days)", deleted, retention_days)
    except Exception as e:
        logger.warning("Login sessions purge failed (non-fatal): %s", e)
    return deleted
