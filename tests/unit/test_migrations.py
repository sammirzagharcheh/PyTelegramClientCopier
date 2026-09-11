"""Unit tests for SQLite migrations, including v11 performance indexes."""

from __future__ import annotations

import pytest

import aiosqlite

from app.config import settings
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

V13_INDEXES = [
    "ix_mapping_transform_rules_mapping_id",
]

V14_INDEXES = [
    "ix_media_assets_user_id",
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


@pytest.mark.asyncio
async def test_migration_v12_creates_schedule_tables(tmp_path):
    """Migration v12 creates user_schedules, mapping_schedules and users.timezone column."""
    settings.sqlite_path = str(tmp_path / "migrations_v12_test.db")
    tmp_path.mkdir(parents=True, exist_ok=True)

    await init_sqlite()

    async with aiosqlite.connect(settings.sqlite_path) as db:
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('user_schedules', 'mapping_schedules')"
        ) as cur:
            tables = {r[0] for r in await cur.fetchall()}
        assert "user_schedules" in tables
        assert "mapping_schedules" in tables

        async with db.execute("PRAGMA table_info(users)") as cur:
            cols = {r[1] for r in await cur.fetchall()}
        assert "timezone" in cols


@pytest.mark.asyncio
async def test_migration_v13_creates_transform_rules_table(tmp_path):
    """Migration v13 creates mapping_transform_rules and index."""
    settings.sqlite_path = str(tmp_path / "migrations_v13_test.db")
    tmp_path.mkdir(parents=True, exist_ok=True)

    await init_sqlite()

    async with aiosqlite.connect(settings.sqlite_path) as db:
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = 'mapping_transform_rules'"
        ) as cur:
            tables = [r[0] for r in await cur.fetchall()]
        assert "mapping_transform_rules" in tables

        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name IS NOT NULL"
        ) as cur:
            rows = await cur.fetchall()
        index_names = {r[0] for r in rows}
        for idx_name in V13_INDEXES:
            assert idx_name in index_names, f"Expected index {idx_name} from migration v13"


@pytest.mark.asyncio
async def test_migration_v14_creates_media_assets_and_transform_columns(tmp_path):
    """Migration v14 creates media_assets and media replacement columns on transform rules."""
    settings.sqlite_path = str(tmp_path / "migrations_v14_test.db")
    tmp_path.mkdir(parents=True, exist_ok=True)

    await init_sqlite()

    async with aiosqlite.connect(settings.sqlite_path) as db:
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = 'media_assets'"
        ) as cur:
            tables = [r[0] for r in await cur.fetchall()]
        assert "media_assets" in tables

        async with db.execute(
            "PRAGMA table_info(mapping_transform_rules)"
        ) as cur:
            cols = {r[1] for r in await cur.fetchall()}
        assert "replacement_media_asset_id" in cols
        assert "apply_to_media_types" in cols

        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name IS NOT NULL"
        ) as cur:
            rows = await cur.fetchall()
        index_names = {r[0] for r in rows}
        for idx_name in V14_INDEXES:
            assert idx_name in index_names, f"Expected index {idx_name} from migration v14"


@pytest.mark.asyncio
async def test_migration_v17_adds_dest_message_index_updated_at(tmp_path):
    """Migration v17 adds dest_message_index.updated_at for UI timestamps."""
    settings.sqlite_path = str(tmp_path / "migrations_v17_test.db")
    tmp_path.mkdir(parents=True, exist_ok=True)

    await init_sqlite()

    async with aiosqlite.connect(settings.sqlite_path) as db:
        async with db.execute("PRAGMA table_info(dest_message_index)") as cur:
            cols = {r[1] for r in await cur.fetchall()}
        assert "updated_at" in cols


@pytest.mark.asyncio
async def test_migration_v18_through_v23_schema(tmp_path):
    """v18 heartbeat, v19 alert webhooks, v20+v23 mapping columns, v21 filter columns, v22 api keys."""
    settings.sqlite_path = str(tmp_path / "migrations_v18_23.db")
    tmp_path.mkdir(parents=True, exist_ok=True)
    await init_sqlite()
    async with aiosqlite.connect(settings.sqlite_path) as db:
        async with db.execute("PRAGMA table_info(worker_registry)") as cur:
            wr_cols = {r[1] for r in await cur.fetchall()}
        assert "last_heartbeat_at" in wr_cols

        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = 'user_alert_webhooks'"
        ) as cur:
            assert await cur.fetchone()

        async with db.execute("PRAGMA table_info(channel_mappings)") as cur:
            cm_cols = {r[1] for r in await cur.fetchall()}
        for c in (
            "send_delay_ms",
            "sync_edits",
            "edit_strategy",
            "sync_deletes",
            "copy_webhook_url",
            "copy_webhook_secret",
            "copy_webhook_payload_template",
            "copy_webhook_secret_header_name",
            "copy_webhook_secret_header_value",
            "copy_webhook_secret_mode",
        ):
            assert c in cm_cols

        async with db.execute("PRAGMA table_info(mapping_filters)") as cur:
            mf_cols = {r[1] for r in await cur.fetchall()}
        for c in (
            "allowed_sender_ids",
            "denied_usernames",
            "min_url_count",
            "max_url_count",
            "required_hashtags",
        ):
            assert c in mf_cols

        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = 'user_api_keys'"
        ) as cur:
            assert await cur.fetchone()
