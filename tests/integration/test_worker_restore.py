"""Integration tests for worker restoration on API startup."""

from unittest.mock import MagicMock, patch

import pytest

from app.db.sqlite import get_sqlite, init_sqlite
from app.web.routers import workers


@pytest.fixture
async def db_with_active_account(tmp_path):
    """Set up SQLite with a user and active telegram account."""
    db_path = tmp_path / "test.db"
    import app.config as config

    config.settings.sqlite_path = str(db_path)
    await init_sqlite()
    conn = await get_sqlite()
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
async def test_restore_spawns_bot_worker_from_sentinel_path(tmp_path):
    from app.config import settings
    from app.db.sqlite import get_sqlite, init_sqlite
    from app.telegram.worker_account import bot_registry_path

    settings.sqlite_path = str(tmp_path / "bot-restore.db")
    await init_sqlite()
    db = await get_sqlite()
    await db.execute(
        "INSERT INTO users (id, email, role, status) VALUES (?, ?, ?, ?)",
        (1, "user@example.com", "user", "active"),
    )
    await db.execute(
        "INSERT INTO telegram_accounts (id, user_id, type, bot_token, status, name) VALUES (?, ?, ?, ?, ?, ?)",
        (8, 1, "bot", "123456:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw", "active", "Bot"),
    )
    await db.execute(
        "INSERT INTO worker_registry (worker_id, user_id, account_id, session_path, pid) VALUES (?, ?, ?, ?, ?)",
        ("w8", 1, 8, bot_registry_path(8), 99999),
    )
    await db.commit()

    workers._workers.clear()
    workers._worker_counter = 0
    fake_proc = MagicMock()
    fake_proc.pid = 555
    fake_proc.poll.return_value = None

    with patch("subprocess.Popen", return_value=fake_proc) as mock_popen:
        await workers.restore_workers_from_db(db)

    assert mock_popen.called
    cmd = mock_popen.call_args[0][0]
    joined = " ".join(str(x) for x in cmd)
    assert "123456:" not in joined
    assert "bot://" not in joined
    assert "--account-id" in cmd
    await db.close()
