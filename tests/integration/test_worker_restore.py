"""Integration tests for worker restoration on API startup."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.db.gateway import get_db_connection, init_db
from app.web.routers import workers


@pytest.fixture
async def db_with_active_account(tmp_path):
    """Set up DB with a user and active telegram account."""
    await init_db()
    conn = await get_db_connection()
    await conn.execute("DELETE FROM worker_registry")
    await conn.execute("DELETE FROM refresh_tokens")
    await conn.execute("DELETE FROM login_sessions")
    await conn.execute("DELETE FROM user_alert_webhooks")
    await conn.execute("DELETE FROM user_api_keys")
    await conn.execute("DELETE FROM admin_invites")
    await conn.execute("DELETE FROM media_assets")
    await conn.execute("DELETE FROM dest_message_index")
    await conn.execute("DELETE FROM mapping_transform_rules")
    await conn.execute("DELETE FROM mapping_filters")
    await conn.execute("DELETE FROM mapping_schedules")
    await conn.execute("DELETE FROM user_schedules")
    await conn.execute("DELETE FROM channel_mappings")
    await conn.execute("DELETE FROM telegram_accounts")
    await conn.execute("DELETE FROM users")
    await conn.execute(
        "INSERT INTO users (id, email, role, status) VALUES (?, ?, ?, ?)",
        (1, "user@example.com", "user", "active"),
    )
    await conn.execute(
        "INSERT INTO telegram_accounts (id, user_id, type, session_path, status) VALUES (?, ?, ?, ?, ?)",
        (1, 1, "user", str(tmp_path / "dummy.session"), "active"),
    )
    await conn.commit()
    try:
        yield conn
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_restore_does_not_auto_start_workers(db_with_active_account):
    """restore_workers_from_db does NOT auto-start workers for active accounts.
    Only orphan workers (from worker_registry with living PIDs) are reattached."""
    db = db_with_active_account
    workers._workers.clear()
    workers._worker_counter = 0

    with patch("subprocess.Popen") as mock_popen:
        await workers.restore_workers_from_db(db)

    # worker_registry is empty, so no orphans to reattach; should NOT spawn any workers
    assert not mock_popen.called
    assert len(workers._workers) == 0


@pytest.mark.asyncio
async def test_restore_spawns_workers_for_dead_registry_entries(db_with_active_account):
    """When worker_registry has rows with dead PIDs (e.g. after graceful shutdown),
    restore spawns new workers for those accounts."""
    db = db_with_active_account
    workers._workers.clear()
    workers._worker_counter = 0

    async with db.execute("SELECT session_path FROM telegram_accounts WHERE id = 1") as cur:
        row = await cur.fetchone()
    session_path = row[0]

    await db.execute(
        "INSERT INTO worker_registry (worker_id, user_id, account_id, session_path, pid) VALUES (?, ?, ?, ?, ?)",
        ("w1", 1, 1, session_path, 99999),
    )
    await db.commit()

    fake_proc = MagicMock()
    fake_proc.pid = 12345
    fake_proc.poll.return_value = None

    with patch("subprocess.Popen", return_value=fake_proc) as mock_popen:
        await workers.restore_workers_from_db(db)

    assert mock_popen.called
    assert len(workers._workers) == 1
    w = list(workers._workers.values())[0]
    assert w["account_id"] == 1
    assert "started_at" in w
    assert w["started_at"] is not None

    await workers.terminate_all_workers(db)


@pytest.mark.asyncio
async def test_restore_does_not_spawn_from_inflight_reservation(db_with_active_account):
    """Reservation rows (pid=-1) represent an in-progress start and must not spawn duplicates."""
    db = db_with_active_account
    workers._workers.clear()
    workers._worker_counter = 0

    async with db.execute("SELECT session_path FROM telegram_accounts WHERE id = 1") as cur:
        row = await cur.fetchone()
    session_path = row[0]

    await db.execute(
        "INSERT INTO worker_registry (worker_id, user_id, account_id, session_path, pid) VALUES (?, ?, ?, ?, ?)",
        ("w_reserve_restore", 1, 1, session_path, -1),
    )
    await db.commit()

    with patch("subprocess.Popen") as mock_popen:
        await workers.restore_workers_from_db(db)

    assert not mock_popen.called
    assert len(workers._workers) == 0


@pytest.mark.asyncio
async def test_restore_spawns_from_stale_inflight_reservation(db_with_active_account):
    """Stale reservation rows should be treated as dead launchers and recovered."""
    db = db_with_active_account
    workers._workers.clear()
    workers._worker_counter = 0

    async with db.execute("SELECT session_path FROM telegram_accounts WHERE id = 1") as cur:
        row = await cur.fetchone()
    session_path = row[0]

    stale_created_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    await db.execute(
        "INSERT INTO worker_registry (worker_id, user_id, account_id, session_path, pid, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("w_stale_restore", 1, 1, session_path, -1, stale_created_at),
    )
    await db.commit()

    fake_proc = MagicMock()
    fake_proc.pid = 12348
    fake_proc.poll.return_value = None
    with patch("subprocess.Popen", return_value=fake_proc) as mock_popen:
        await workers.restore_workers_from_db(db)

    assert mock_popen.called
    assert len(workers._workers) == 1
