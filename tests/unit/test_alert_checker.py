"""Unit tests for stale worker alert checker."""

import os
from datetime import datetime, timedelta, timezone

import pytest

import aiosqlite

from app.config import settings
from app.db.sqlite import init_sqlite
from app.services.alert_checker import check_stale_workers_and_alert


@pytest.mark.asyncio
async def test_alert_checker_sends_when_stale_heartbeat(tmp_path, monkeypatch):
    settings.sqlite_path = str(tmp_path / "alert.db")
    await init_sqlite()
    db = await aiosqlite.connect(settings.sqlite_path)
    try:
        await db.execute(
            "INSERT INTO users (email, role, status, password_hash, name) VALUES (?, ?, ?, ?, ?)",
            ("a@b.com", "user", "active", "x", "A"),
        )
        await db.execute(
            "INSERT INTO user_alert_webhooks (user_id, url, secret, enabled) VALUES (1, ?, NULL, 1)",
            ("http://example.invalid/webhook",),
        )
        old = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        pid = os.getpid()
        await db.execute(
            "INSERT INTO worker_registry (worker_id, user_id, account_id, session_path, pid, created_at, last_heartbeat_at) "
            "VALUES (?, 1, 1, 's.session', ?, ?, ?)",
            ("wtest", pid, old, old),
        )
        await db.commit()

        posted: list[dict] = []

        async def fake_post(url, secret, payload):
            posted.append({"url": url, "payload": payload})

        import app.services.alert_checker as ac

        monkeypatch.setattr(ac, "post_json_webhook", fake_post)
        n = await check_stale_workers_and_alert(db)
        assert n >= 1
        assert posted and posted[0]["payload"]["type"] == "worker_stale_heartbeat"
    finally:
        await db.close()
