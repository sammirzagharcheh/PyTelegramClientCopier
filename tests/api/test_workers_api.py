"""API tests for workers endpoints (start, stop, list)."""

import os
from unittest.mock import MagicMock, patch

import pytest

from app.db.sqlite import get_sqlite
from app.web.routers import workers


@pytest.fixture(autouse=True)
def reset_worker_registry():
    """Reset in-memory worker registry before/after each test."""
    workers._workers.clear()
    workers._worker_counter = 0
    yield
    workers._workers.clear()
    workers._worker_counter = 0


def test_start_worker_with_stale_registry_succeeds(api_client, user_token):
    """When worker_registry has a row with dead PID, POST /workers/start prunes it and spawns."""
    # Insert stale worker_registry row (PID 99999 does not exist)
    async def add_stale_row():
        db = await get_sqlite()
        session_path = "dummy.session"
        await db.execute(
            "INSERT INTO worker_registry (worker_id, user_id, account_id, session_path, pid) VALUES (?, ?, ?, ?, ?)",
            ("w_stale", 1, 1, session_path, 99999),
        )
        await db.commit()
        await db.close()

    import asyncio

    asyncio.run(add_stale_row())

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
    fake_proc.pid = os.getpid()  # Use current process PID so registry liveness check passes
    fake_proc.poll.return_value = None

    with patch("app.web.routers.workers.subprocess.Popen", return_value=fake_proc):
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


def test_list_workers_reattaches_from_registry_when_missing_from_memory(api_client, user_token):
    """When worker_registry has a row with alive PID but worker is not in _workers
    (e.g. started by another API instance), list_workers returns it and reattaches."""
    workers._workers.clear()
    alive_pid = os.getpid()

    async def add_registry_row():
        import asyncio

        db = await get_sqlite()
        await db.execute(
            "INSERT INTO worker_registry (worker_id, user_id, account_id, session_path, pid) VALUES (?, ?, ?, ?, ?)",
            ("w99", 1, 1, "data/user1.session", alive_pid),
        )
        await db.commit()
        await db.close()

    import asyncio

    asyncio.run(add_registry_row())

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
