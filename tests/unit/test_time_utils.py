from datetime import datetime, timezone

from app.utils.time import normalize_utc_iso_for_json


def test_normalize_datetime_object_to_utc_z() -> None:
    value = datetime(2026, 5, 1, 12, 34, 56, tzinfo=timezone.utc)
    assert normalize_utc_iso_for_json(value) == "2026-05-01T12:34:56Z"


def test_normalize_space_plus00_to_utc_z() -> None:
    value = "2026-05-01 12:34:56+00:00"
    assert normalize_utc_iso_for_json(value) == "2026-05-01T12:34:56Z"


def test_normalize_legacy_sqlite_space_format() -> None:
    value = "2026-05-01 12:34:56"
    assert normalize_utc_iso_for_json(value) == "2026-05-01T12:34:56Z"
