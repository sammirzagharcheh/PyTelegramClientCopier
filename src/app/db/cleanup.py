"""Database cleanup tasks."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.db.sqlite import get_sqlite

logger = logging.getLogger(__name__)


async def purge_old_login_sessions(retention_days: int) -> int:
    """
    Delete completed/cancelled login_sessions older than retention_days.
    Pending sessions are never deleted.
    Returns number of rows deleted.
    """
    deleted = 0
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
        db = await get_sqlite()
        try:
            cursor = await db.execute(
                """
                DELETE FROM login_sessions
                WHERE status IN ('completed', 'cancelled')
                AND created_at < ?
                """,
                (cutoff,),
            )
            await db.commit()
            deleted = cursor.rowcount
        finally:
            await db.close()
        if deleted:
            logger.info("Purged %d old login_sessions rows (retention=%d days)", deleted, retention_days)
    except Exception as e:
        logger.warning("Login sessions purge failed (non-fatal): %s", e)
    return deleted
