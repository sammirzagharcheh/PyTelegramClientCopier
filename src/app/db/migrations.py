"""Legacy SQLite migration module (deprecated).

The project now runs PostgreSQL-only and schema management is handled by Alembic.
These helpers are intentionally disabled.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

async def ensure_migrations_table(db) -> None:  # pragma: no cover - legacy path
    logger.warning("ensure_migrations_table() is deprecated in PostgreSQL-only mode")


async def get_applied_migrations(db) -> set[str]:  # pragma: no cover - legacy path
    logger.warning("get_applied_migrations() is deprecated in PostgreSQL-only mode")
    return set()


async def run_migrations(db) -> None:  # pragma: no cover - legacy path
    logger.warning("run_migrations() is deprecated; use Alembic migrations")
