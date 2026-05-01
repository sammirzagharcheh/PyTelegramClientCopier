"""Deprecated SQLite gateway module.

This project is PostgreSQL-only. Keep these aliases temporarily so older imports
continue to work while call sites migrate to app.db.gateway.
"""

from __future__ import annotations

from app.db.gateway import get_db_connection as get_sqlite
from app.db.gateway import init_db as init_sqlite

__all__ = ["get_sqlite", "init_sqlite"]

