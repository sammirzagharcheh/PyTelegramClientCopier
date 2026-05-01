"""Database cleanup tasks."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.db.gateway import get_db_connection
from app.utils.time import sql_ts_expr

logger = logging.getLogger(__name__)


async def purge_old_login_sessions(retention_days: int) -> int:
    """
    Delete completed/cancelled login_sessions older than retention_days.
    Pending sessions are never deleted.
    Returns number of rows deleted.
    """
    deleted = 0
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        db = await get_db_connection()
        try:
            created_expr = sql_ts_expr("created_at")
            cutoff_expr = sql_ts_expr("?")
            cursor = await db.execute(
                f"""
                DELETE FROM login_sessions
                WHERE status IN ('completed', 'cancelled')
                AND {created_expr} < {cutoff_expr}
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
