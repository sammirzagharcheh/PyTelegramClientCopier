"""API tests for workers endpoints (start, stop, list)."""

import asyncio
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from app.db.gateway import get_db_connection
from app.web.routers import workers

pytestmark = pytest.mark.skipif(
    sys.platform == "win32",
    reason="Worker API async/process tests are unstable on local Windows runtime",
)


def _run_async(coro):
    """Run async code from sync test; avoids event loop conflicts."""
    return asyncio.run(coro)


def _clear_worker_registry_db_sync() -> None:
    """Clear persistent registry between tests."""
    async def _clear() -> None:
        db = await get_db_connection()
        try:
            await db.execute("DELETE FROM worker_registry")
            await db.commit()
        finally:
            await db.close()

    asyncio.run(_clear())


@pytest.fixture(autouse=True)
def reset_worker_registry():
    """Reset in-memory worker registry and persistent table after each test."""
    workers._workers.clear()
    workers._worker_counter = 0
    workers._account_worker_locks.clear()
    yield
    _clear_worker_registry_db_sync()
    workers._workers.clear()
    workers._worker_counter = 0
    workers._account_worker_locks.clear()


def test_start_worker_with_stale_registry_succeeds(api_client, user_token):
    """When worker_registry has a row with dead PID, POST /workers/start prunes it and spawns."""
    # Insert stale worker_registry row (PID 99999 does not exist)
    async def add_stale_row():
        db = await get_db_connection()
        session_path = "dummy.session"
        await db.execute(
            "INSERT INTO worker_registry (worker_id, user_id, account_id, session_path, pid) VALUES (?, ?, ?, ?, ?)",
            ("w_stale", 1, 1, session_path, 99999),
        )
        await db.commit()
        await db.close()

    _run_async(add_stale_row())

    fake_proc = MagicMock()
    fake_proc.pid = 12345
    fake_proc.poll.return_value = None

    with patch("app.web.routers.workers.subprocess.Popen", return_value=fake_proc):
        r = api_client.post(
            "/api/workers/start",
            params={"account_id": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )

    assert r.status_code == 200
    data = r.json()
    assert data["account_id"] == 1
    assert data["user_id"] == 1
    assert "id" in data
    assert data["pid"] == 12345
    assert "started_at" in data
    assert data["started_at"] is not None


def test_list_workers_returns_started_at(api_client, user_token):
    """GET /workers includes started_at for each running worker."""
    fake_proc = MagicMock()
    fake_proc.pid = 424241
    fake_proc.poll.return_value = None

    # Avoid relying on a real OS PID for liveness checks in CI.
    with (
        patch("app.web.routers.workers.subprocess.Popen", return_value=fake_proc),
        patch("app.web.routers.workers._pid_alive", return_value=True),
    ):
        api_client.post(
            "/api/workers/start",
            params={"account_id": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )

        r = api_client.get(
            "/api/workers",
            headers={"Authorization": f"Bearer {user_token}"},
        )
    assert r.status_code == 200
    workers_list = r.json()
    assert len(workers_list) >= 1
    w = next(ww for ww in workers_list if ww.get("account_id") == 1 and ww.get("running"))
    assert "started_at" in w
    assert w["started_at"] is not None


def test_start_worker_same_account_twice_returns_conflict(api_client, user_token):
    """Starting an already-running account twice must return 409 on second request."""
    fake_proc = MagicMock()
    fake_proc.pid = 12346
    fake_proc.poll.return_value = None

    with patch("app.web.routers.workers.subprocess.Popen", return_value=fake_proc) as popen_mock:
        first = api_client.post(
            "/api/workers/start",
            params={"account_id": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        second = api_client.post(
            "/api/workers/start",
            params={"account_id": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )

    assert first.status_code == 200
    assert second.status_code == 409
    assert popen_mock.call_count == 1


def test_list_workers_reattaches_from_registry_when_missing_from_memory(api_client, user_token):
    """When worker_registry has a row with alive PID but worker is not in _workers
    (e.g. started by another API instance), list_workers returns it and reattaches."""
    workers._workers.clear()
    alive_pid = 424242

    async def add_registry_row():
        db = await get_db_connection()
        await db.execute(
            "INSERT INTO worker_registry (worker_id, user_id, account_id, session_path, pid) VALUES (?, ?, ?, ?, ?)",
            ("w99", 1, 1, "data/user1.session", alive_pid),
        )
        await db.commit()
        await db.close()

    _run_async(add_registry_row())

    # Avoid real-PID coupling in CI: emulate liveness check deterministically.
    with patch("app.web.routers.workers._pid_alive", return_value=True):
        r = api_client.get(
            "/api/workers",
            headers={"Authorization": f"Bearer {user_token}"},
        )
    assert r.status_code == 200
    workers_list = r.json()
    assert len(workers_list) == 1
    w = workers_list[0]
    assert w["id"] == "w99"
    assert w["account_id"] == 1
    assert w["running"] is True
    assert w["pid"] == alive_pid
    assert "w99" in workers._workers


def test_spawn_worker_concurrent_start_collision_single_reservation(api_client):
    """Concurrent starts for same account should reserve only one worker slot."""

    async def run_collision():
        db = await get_db_connection()
        fake_proc = MagicMock()
        fake_proc.pid = 424243
        fake_proc.poll.return_value = None

        with patch("app.web.routers.workers.subprocess.Popen", return_value=fake_proc):
            first, second = await asyncio.gather(
                workers._spawn_worker_for_account(db, 1, 1, "data/user1.session"),
                workers._spawn_worker_for_account(db, 1, 1, "data/user1.session"),
            )

        async with db.execute(
            "SELECT COUNT(*) FROM worker_registry WHERE account_id = ?",
            (1,),
        ) as cur:
            cnt = (await cur.fetchone())[0]
        await db.close()
        return first, second, cnt

    first, second, cnt = _run_async(run_collision())
    assert (first, second).count(True) == 1
    assert cnt == 1


