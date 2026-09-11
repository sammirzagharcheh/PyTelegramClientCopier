"""Unit tests for Mongo log TTL index catalog."""

from __future__ import annotations

from app.db.mongo_indexes import INDEXES, LOG_TTL_SECONDS, _normalize_index_keys


def test_log_ttl_seconds_is_thirty_days():
    assert LOG_TTL_SECONDS == 60 * 60 * 24 * 30


def test_all_log_collections_have_timestamp_ttl():
    for coll_name in ("message_logs", "worker_logs", "webhook_logs"):
        specs = INDEXES[coll_name]
        ttl_specs = [s for s in specs if s.get("expire_after_seconds") is not None]
        assert len(ttl_specs) == 1, f"{coll_name} should declare exactly one TTL index"
        ttl = ttl_specs[0]
        assert ttl["keys"] == [("timestamp", 1)]
        assert ttl["name"] == "ix_ttl_30d"
        assert ttl["expire_after_seconds"] == LOG_TTL_SECONDS


def test_normalize_index_keys_from_motor_style():
    assert _normalize_index_keys([("timestamp", 1)]) == [("timestamp", 1)]
    assert _normalize_index_keys([["user_id", 1], ["timestamp", -1]]) == [
        ("user_id", 1),
        ("timestamp", -1),
    ]
