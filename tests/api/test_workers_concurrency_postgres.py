"""Dedicated PostgreSQL concurrency/retry tests for workers module.

Isolated from test_workers_api.py to avoid shared autouse fixture side effects.
"""

from __future__ import annotations

import asyncio
import os
import types
from unittest.mock import MagicMock, patch

import pytest

from app.db.sqlite import get_sqlite, init_sqlite
from app.web.routers import workers

pytestmark = pytest.mark.postgres_concurrency


def _run_async(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def isolate_workers_state():
    workers._workers.clear()
    workers._worker_counter = 0
    workers._account_worker_locks.clear()
    yield
    workers._workers.clear()
    workers._worker_counter = 0
    workers._account_worker_locks.clear()


@pytest.fixture(autouse=True)
def postgres_backend(monkeypatch):
    monkeypatch.setattr("app.config.settings.db_backend", "postgres")
    monkeypatch.setattr(
        "app.config.settings.database_url",
        "postgresql+asyncpg://8n8user:8N8p%40ssw0rd@localhost:5432/8n8DataBase",
    )


def test_spawn_worker_concurrent_start_collision_single_reservation_postgres_mode():
    """Postgres mode: concurrent starts should reserve only one slot."""

    async def run_collision():
        await init_sqlite()
        db_cleanup = await get_sqlite()
        await db_cleanup.execute("DELETE FROM worker_registry WHERE account_id = ?", (1,))
        await db_cleanup.commit()
        await db_cleanup.close()

        fake_proc = MagicMock()
        fake_proc.pid = os.getpid()
        fake_proc.poll.return_value = None

        db1 = await get_sqlite()
        db2 = await get_sqlite()
        ready_count = 0
        ready_lock = asyncio.Lock()
        start_event = asyncio.Event()

        async def run_spawn(conn):
            nonlocal ready_count
            async with ready_lock:
                ready_count += 1
                if ready_count == 2:
                    start_event.set()
            await start_event.wait()
            return await workers._spawn_worker_for_account(conn, 1, 1, "data/user1.session")

        try:
            with patch("app.web.routers.workers.subprocess.Popen", return_value=fake_proc):
                first, second = await asyncio.wait_for(
                    asyncio.gather(run_spawn(db1), run_spawn(db2)),
                    timeout=5.0,
                )
        finally:
            await db1.close()
            await db2.close()

        db_check = await get_sqlite()
        async with db_check.execute(
            "SELECT COUNT(*) FROM worker_registry WHERE account_id = ?",
            (1,),
        ) as cur:
            cnt = (await cur.fetchone())[0]
        await db_check.execute("DELETE FROM worker_registry WHERE account_id = ?", (1,))
        await db_check.commit()
        await db_check.close()
        return first, second, cnt

    first, second, cnt = _run_async(run_collision())
    assert (first, second).count(True) == 1
    assert cnt == 1


def test_retry_wrapper_retries_on_transient_sqlstate():
    """Transient 40P01/40001 failures should be retried and then succeed."""

    class FakeTransientError(Exception):
        def __init__(self, msg: str, sqlstate: str):
            super().__init__(msg)
            self.sqlstate = sqlstate

    async def run_retry_case():
        await init_sqlite()
        db = await get_sqlite()
        await db.execute("DELETE FROM worker_registry WHERE account_id = ?", (1,))
        await db.commit()
        attempts = {"count": 0}
        original_impl = db._execute_impl

        async def flaky_impl(self, sql, params=None):
            if "INSERT INTO worker_registry" in str(sql) and attempts["count"] < 2:
                attempts["count"] += 1
                code = "40P01" if attempts["count"] == 1 else "40001"
                raise FakeTransientError(f"simulated transient {code}", code)
            return await original_impl(sql, params)

        db._execute_impl = types.MethodType(flaky_impl, db)

        fake_proc = MagicMock()
        fake_proc.pid = os.getpid()
        fake_proc.poll.return_value = None
        with patch("app.web.routers.workers.subprocess.Popen", return_value=fake_proc):
            ok = await workers._spawn_worker_for_account(db, 1, 1, "data/user1.session")

        async with db.execute(
            "SELECT COUNT(*) FROM worker_registry WHERE account_id = ?",
            (1,),
        ) as cur:
            cnt = (await cur.fetchone())[0]
        await db.execute("DELETE FROM worker_registry WHERE account_id = ?", (1,))
        await db.commit()
        await db.close()
        return ok, cnt, attempts["count"]

    ok, cnt, attempts = _run_async(run_retry_case())
    assert ok is True
    assert cnt == 1
    assert attempts == 2


def test_prune_orphaned_registry_keeps_inflight_reservations():
    """Reservation rows (pid=-1) must not be pruned as dead workers."""

    async def run_case():
        await init_sqlite()
        db = await get_sqlite()
        await db.execute("DELETE FROM worker_registry WHERE account_id = ?", (1,))
        await db.execute(
            "INSERT INTO worker_registry (worker_id, user_id, account_id, session_path, pid) VALUES (?, ?, ?, ?, ?)",
            ("w_reserve", 1, 1, "data/user1.session", -1),
        )
        await db.commit()
        await workers._prune_orphaned_registry_rows(db)
        async with db.execute(
            "SELECT COUNT(*) FROM worker_registry WHERE worker_id = ?",
            ("w_reserve",),
        ) as cur:
            cnt = (await cur.fetchone())[0]
        await db.execute("DELETE FROM worker_registry WHERE worker_id = ?", ("w_reserve",))
        await db.commit()
        await db.close()
        return cnt

    remaining = _run_async(run_case())
    assert remaining == 1


def test_stop_workers_preserves_inflight_reservation_rows():
    """Stopping account workers should not delete a still-inflight reservation row."""

    async def run_case():
        await init_sqlite()
        db = await get_sqlite()
        await db.execute("DELETE FROM worker_registry WHERE account_id = ?", (1,))
        await db.execute(
            "INSERT INTO worker_registry (worker_id, user_id, account_id, session_path, pid) VALUES (?, ?, ?, ?, ?)",
            ("w_reserve_stop", 1, 1, "data/user1.session", -1),
        )
        await db.commit()
        await workers.stop_workers_for_account(1, db)
        async with db.execute(
            "SELECT COUNT(*) FROM worker_registry WHERE worker_id = ?",
            ("w_reserve_stop",),
        ) as cur:
            cnt = (await cur.fetchone())[0]
        await db.execute("DELETE FROM worker_registry WHERE worker_id = ?", ("w_reserve_stop",))
        await db.commit()
        await db.close()
        return cnt

    remaining = _run_async(run_case())
    assert remaining == 1
