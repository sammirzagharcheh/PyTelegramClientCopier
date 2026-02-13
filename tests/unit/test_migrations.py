"""Unit tests for SQLite migrations, including v11 performance indexes."""

from __future__ import annotations

import pytest

import aiosqlite

from app.config import settings
from app.db.migrations import run_migrations
from app.db.sqlite import init_sqlite

# Indexes created by migration v11
V11_INDEXES = [
    "ix_users_id_status",
    "ix_telegram_accounts_user_id",
    "ix_telegram_accounts_user_status",
    "ix_channel_mappings_user_id",
    "ix_channel_mappings_user_src_dest",
    "ix_mapping_filters_mapping_id",
    "ix_dest_message_index_user_id",
]


@pytest.mark.asyncio
async def test_migration_v11_creates_indexes(tmp_path):
    """Migration v11 creates all performance indexes."""
    settings.sqlite_path = str(tmp_path / "migrations_test.db")
    tmp_path.mkdir(parents=True, exist_ok=True)

    await init_sqlite()

    async with aiosqlite.connect(settings.sqlite_path) as db:
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name IS NOT NULL"
        ) as cur:
            rows = await cur.fetchall()
    index_names = {r[0] for r in rows}

    for idx_name in V11_INDEXES:
        assert idx_name in index_names, f"Expected index {idx_name} from migration v11"
