"""Unit tests for stale worker alert checker helpers."""

import os

from app.services.alert_checker import _parse_iso_utc, _pid_alive


def test_parse_iso_utc_accepts_offset_and_z():
    dt = _parse_iso_utc("2020-01-02T03:04:05+00:00")
    assert dt is not None
    assert dt.tzinfo is not None
    assert _parse_iso_utc("2020-01-02T03:04:05Z") is not None
    assert _parse_iso_utc(None) is None
    assert _parse_iso_utc("not-a-date") is None


def test_pid_alive_current_process():
    assert _pid_alive(os.getpid()) is True
