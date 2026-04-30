from __future__ import annotations

import pytest

pytestmark = pytest.mark.postgres_parity


@pytest.mark.asyncio
async def test_postgres_schema_contains_core_tables(postgres_db):
    db = postgres_db
    async with db.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name IN ('users', 'channel_mappings', 'mapping_filters', 'dest_message_index')"
    ) as cur:
        rows = await cur.fetchall()
    names = {r[0] for r in rows}
    assert "users" in names
    assert "channel_mappings" in names
    assert "mapping_filters" in names
    assert "dest_message_index" in names


@pytest.mark.asyncio
async def test_postgres_schema_contains_phase_columns(postgres_db):
    db = postgres_db
    async with db.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = 'worker_registry'"
    ) as cur:
        wr_cols = {r[0] for r in await cur.fetchall()}
    assert "last_heartbeat_at" in wr_cols

    async with db.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = 'channel_mappings'"
    ) as cur:
        cm_cols = {r[0] for r in await cur.fetchall()}
    for col in (
        "send_delay_ms",
        "sync_edits",
        "edit_strategy",
        "sync_deletes",
        "copy_webhook_payload_template",
        "copy_webhook_secret_mode",
    ):
        assert col in cm_cols
