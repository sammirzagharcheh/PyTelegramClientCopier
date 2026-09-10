"""Unit tests for stale worker alert checker helpers."""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.alert_checker import (
    STALE_HEARTBEAT_SECONDS,
    _last_alert_at,
    _parse_iso_utc,
    _pid_alive,
    check_stale_workers_and_alert,
)


def test_parse_iso_utc_accepts_offset_and_z():
    dt = _parse_iso_utc("2020-01-02T03:04:05+00:00")
    assert dt is not None
    assert dt.tzinfo is not None
    assert _parse_iso_utc("2020-01-02T03:04:05Z") is not None
    assert _parse_iso_utc(None) is None
    assert _parse_iso_utc("not-a-date") is None


def test_pid_alive_current_process():
    import os

    assert _pid_alive(os.getpid()) is True


@pytest.mark.asyncio
async def test_alert_checker_sends_when_stale_heartbeat(monkeypatch):
    """Drive checker with a fake DB; bypass pid check via monkeypatch on module global."""
    _last_alert_at.clear()
    old = (datetime.now(timezone.utc) - timedelta(seconds=STALE_HEARTBEAT_SECONDS * 2)).strftime(
        "%Y-%m-%dT%H:%M:%S+00:00"
    )

    class Cur:
        def __init__(self, rows):
            self.rows = rows

        async def fetchall(self):
            return self.rows

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    class DB:
        def execute(self, sql, params=None):
            if "worker_registry" in sql:
                return Cur([("w1", 1, 1, 1, old, old)])
            return Cur([("http://example.invalid/hook", None)])

    posted: list = []

    async def fake_post(url, secret, payload):
        posted.append(payload)

    monkeypatch.setattr("app.services.alert_checker._pid_alive", lambda _p: True)
    monkeypatch.setattr("app.services.alert_checker.post_json_webhook", fake_post)

    n = await check_stale_workers_and_alert(DB())
    assert n == 1
    assert posted[0]["type"] == "worker_stale_heartbeat"
