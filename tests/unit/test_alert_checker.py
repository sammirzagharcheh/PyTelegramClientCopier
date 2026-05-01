"""Unit tests for stale worker alert checker."""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.alert_checker import check_stale_workers_and_alert


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def fetchall(self):
        return self._rows


class _FakeDb:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, _sql, _params=None):
        return _FakeCursor(self._rows)


@pytest.mark.asyncio
async def test_alert_checker_sends_when_stale_heartbeat(monkeypatch):
    old = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    rows = [("wtest", 1, 1, 424244, old, old)]
    db = _FakeDb(rows)

    posted: list[dict] = []

    async def fake_post(url, secret, payload):
        posted.append({"url": url, "payload": payload})

    async def fake_hooks(_db, _user_id):
        return [("http://example.invalid/webhook", None)]

    import app.services.alert_checker as ac

    ac._last_alert_at.clear()
    monkeypatch.setattr(ac, "post_json_webhook", fake_post)
    monkeypatch.setattr(ac, "_list_alert_webhooks", fake_hooks)
    monkeypatch.setattr(ac, "_pid_alive", lambda _pid: True)
    n = await check_stale_workers_and_alert(db)
    assert n == 1
    assert posted and posted[0]["payload"]["type"] == "worker_stale_heartbeat"
