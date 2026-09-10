"""Unit tests for stale worker alert checker."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.services.alert_checker import STALE_HEARTBEAT_SECONDS, _last_alert_at


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
    def __init__(self, worker_rows, hook_rows):
        self._worker_rows = worker_rows
        self._hook_rows = hook_rows

    def execute(self, sql, params=None):
        if "worker_registry" in sql:
            return _FakeCursor(self._worker_rows)
        if "user_alert_webhooks" in sql:
            return _FakeCursor(self._hook_rows)
        return _FakeCursor([])


@pytest.mark.asyncio
async def test_alert_checker_sends_when_stale_heartbeat():
    _last_alert_at.clear()
    old = (datetime.now(timezone.utc) - timedelta(seconds=STALE_HEARTBEAT_SECONDS + 60)).isoformat()
    db = _FakeDB(
        worker_rows=[("wtest", 1, 1, 12345, old, old)],
        hook_rows=[("http://example.invalid/webhook", None)],
    )
    posted: list[dict] = []

    async def fake_post(url, secret, payload):
        posted.append({"url": url, "payload": payload})

    with patch("app.services.alert_checker._pid_alive", return_value=True), patch(
        "app.services.alert_checker.post_json_webhook",
        new=AsyncMock(side_effect=fake_post),
    ):
        from app.services.alert_checker import check_stale_workers_and_alert

        n = await check_stale_workers_and_alert(db)

    assert n >= 1, f"expected alerts, got {n}; posted={posted}"
    assert posted and posted[0]["payload"]["type"] == "worker_stale_heartbeat"
