"""Unit tests for stale worker alert checker."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.services import alert_checker as ac


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    async def fetchall(self):
        return self._rows

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class _FakeDB:
    def __init__(self):
        self.calls: list[str] = []
        old = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        self._workers = [("wtest", 1, 1, 12345, old, old)]
        self._hooks = [("http://example.invalid/webhook", None)]

    def execute(self, sql, params=None):
        self.calls.append(sql)
        if "worker_registry" in sql:
            return _FakeCursor(self._workers)
        if "user_alert_webhooks" in sql:
            return _FakeCursor(self._hooks)
        return _FakeCursor([])


@pytest.mark.asyncio
async def test_alert_checker_sends_when_stale_heartbeat():
    ac._last_alert_at.clear()
    db = _FakeDB()
    posted: list[dict] = []

    async def fake_post(url, secret, payload):
        posted.append({"url": url, "payload": payload})

    with patch.object(ac, "_pid_alive", return_value=True), patch.object(
        ac, "post_json_webhook", new=AsyncMock(side_effect=fake_post)
    ):
        n = await ac.check_stale_workers_and_alert(db)

    assert n >= 1, (
        f"expected alerts, got {n}; posted={posted}; sql_calls={db.calls}; "
        f"cooldown={dict(ac._last_alert_at)}"
    )
    assert posted and posted[0]["payload"]["type"] == "worker_stale_heartbeat"
