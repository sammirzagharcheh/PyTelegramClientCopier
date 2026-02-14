"""Unit tests for schedule logic (_passes_schedule)."""

from __future__ import annotations

import datetime

import pytest

from app.telegram.handlers import _passes_schedule
from app.services.mapping_service import Schedule


def test_passes_schedule_none_always_passes():
    assert _passes_schedule(datetime.datetime(2025, 2, 10, 12, 0, 0, tzinfo=datetime.timezone.utc), None) is True
    assert _passes_schedule(datetime.datetime(2025, 2, 15, 3, 0, 0, tzinfo=datetime.timezone.utc), None) is True


def test_passes_schedule_empty_always_passes():
    empty = Schedule(
        mon_start_utc=None, mon_end_utc=None,
        tue_start_utc=None, tue_end_utc=None,
        wed_start_utc=None, wed_end_utc=None,
        thu_start_utc=None, thu_end_utc=None,
        fri_start_utc=None, fri_end_utc=None,
        sat_start_utc=None, sat_end_utc=None,
        sun_start_utc=None, sun_end_utc=None,
    )
    assert empty.is_empty()
    assert _passes_schedule(datetime.datetime(2025, 2, 10, 12, 0, 0, tzinfo=datetime.timezone.utc), empty) is True


def test_passes_schedule_within_normal_range():
    # Mon 09:00-17:00 UTC; 2025-02-10 is Monday
    sched = Schedule(
        mon_start_utc="09:00", mon_end_utc="17:00",
        tue_start_utc=None, tue_end_utc=None,
        wed_start_utc=None, wed_end_utc=None,
        thu_start_utc=None, thu_end_utc=None,
        fri_start_utc=None, fri_end_utc=None,
        sat_start_utc=None, sat_end_utc=None,
        sun_start_utc=None, sun_end_utc=None,
    )
    # 12:00 UTC Monday - within range
    assert _passes_schedule(datetime.datetime(2025, 2, 10, 12, 0, 0, tzinfo=datetime.timezone.utc), sched) is True
    # 08:00 UTC Monday - outside
    assert _passes_schedule(datetime.datetime(2025, 2, 10, 8, 0, 0, tzinfo=datetime.timezone.utc), sched) is False
    # 18:00 UTC Monday - outside
    assert _passes_schedule(datetime.datetime(2025, 2, 10, 18, 0, 0, tzinfo=datetime.timezone.utc), sched) is False
    # Tuesday - no restriction, passes
    assert _passes_schedule(datetime.datetime(2025, 2, 11, 3, 0, 0, tzinfo=datetime.timezone.utc), sched) is True


def test_passes_schedule_overnight_range():
    # Mon 22:00-02:00 UTC (overnight)
    sched = Schedule(
        mon_start_utc="22:00", mon_end_utc="02:00",
        tue_start_utc=None, tue_end_utc=None,
        wed_start_utc=None, wed_end_utc=None,
        thu_start_utc=None, thu_end_utc=None,
        fri_start_utc=None, fri_end_utc=None,
        sat_start_utc=None, sat_end_utc=None,
        sun_start_utc=None, sun_end_utc=None,
    )
    # Monday 23:00 - within (after start)
    assert _passes_schedule(datetime.datetime(2025, 2, 10, 23, 0, 0, tzinfo=datetime.timezone.utc), sched) is True
    # Monday 01:00 - within (before end)
    assert _passes_schedule(datetime.datetime(2025, 2, 11, 1, 0, 0, tzinfo=datetime.timezone.utc), sched) is True
    # Monday 12:00 - outside (middle of day)
    assert _passes_schedule(datetime.datetime(2025, 2, 10, 12, 0, 0, tzinfo=datetime.timezone.utc), sched) is False
