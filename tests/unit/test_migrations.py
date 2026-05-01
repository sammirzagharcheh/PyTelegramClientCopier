"""Unit tests for PostgreSQL schema bootstrap."""

from __future__ import annotations

import pytest

from app.db.gateway import get_db_connection, init_db

CORE_INDEXES = [
    "ix_users_id_status",
    "ix_telegram_accounts_user_id",
    "ix_telegram_accounts_user_status",
    "ix_channel_mappings_user_id",
    "ix_channel_mappings_user_src_dest",
    "ix_mapping_filters_mapping_id",
    "ix_dest_message_index_user_id",
]

V13_INDEXES = [
    "ix_mapping_transform_rules_mapping_id",
]

V14_INDEXES = [
    "ix_media_assets_user_id",
]


@pytest.mark.asyncio
async def test_postgres_schema_indexes_exist():
    await init_db()
    db = await get_db_connection()
    try:
        async with db.execute(
            "SELECT indexname FROM pg_indexes WHERE schemaname='public'"
        ) as cur:
            rows = await cur.fetchall()
        index_names = {r[0] for r in rows}
        for idx_name in (*CORE_INDEXES, *V13_INDEXES, *V14_INDEXES):
            assert idx_name in index_names
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_postgres_schema_columns_exist():
    await init_db()
    db = await get_db_connection()
    try:
        async with db.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name='worker_registry'"
        ) as cur:
            wr_cols = {r[0] for r in await cur.fetchall()}
        assert "last_heartbeat_at" in wr_cols
        async with db.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name='dest_message_index'"
        ) as cur:
            dmi_cols = {r[0] for r in await cur.fetchall()}
        assert "updated_at" in dmi_cols
    finally:
        await db.close()
