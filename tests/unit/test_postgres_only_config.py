from __future__ import annotations

import pytest

from app.config import Settings


def test_rejects_non_postgres_backend():
    with pytest.raises(ValueError, match="DB_BACKEND must be 'postgres'"):
        Settings(
            db_backend="sqlite",
            database_url="postgresql+asyncpg://8n8user:8N8p%40ssw0rd@localhost:5432/8n8DataBase",
        )
