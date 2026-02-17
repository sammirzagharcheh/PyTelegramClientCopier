"""API tests for workers endpoints (start, stop, list)."""

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
