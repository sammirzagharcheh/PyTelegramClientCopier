"""Unit tests for stale worker alert checker."""

from datetime import datetime, timedelta, timezone

import pytest

import app.services.alert_checker as ac
from app.services.alert_checker import check_stale_workers_and_alert


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
    def execute(self, sql, params=None):
        if "FROM worker_registry" in sql:
            old = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
            return _FakeCursor([("wtest", 1, 1, 12345, old, old)])
        if "FROM user_alert_webhooks" in sql:
            return _FakeCursor([("http://example.invalid/webhook", None)])
        return _FakeCursor([])


@pytest.mark.asyncio
async def test_alert_checker_sends_when_stale_heartbeat(monkeypatch):
    ac._last_alert_at.clear()
    posted: list[dict] = []

    async def fake_post(url, secret, payload):
        posted.append({"url": url, "payload": payload})

    monkeypatch.setattr(ac, "post_json_webhook", fake_post)
    monkeypatch.setattr(ac, "_pid_alive", lambda _pid: True)

    n = await check_stale_workers_and_alert(_FakeDB())
    assert n >= 1
    assert posted and posted[0]["payload"]["type"] == "worker_stale_heartbeat"
