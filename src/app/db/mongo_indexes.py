"""Ensure MongoDB indexes exist for log collections."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Retention for message_logs, worker_logs, and webhook_logs (Mongo TTL).
LOG_TTL_SECONDS = 60 * 60 * 24 * 30

INDEXES = {
    "message_logs": [
        {"keys": [("user_id", 1), ("timestamp", -1)], "name": "ix_user_timestamp"},
        {
            "keys": [("timestamp", 1)],
            "name": "ix_ttl_30d",
            "expire_after_seconds": LOG_TTL_SECONDS,
        },
    ],
    "worker_logs": [
        {"keys": [("user_id", 1), ("timestamp", -1)], "name": "ix_user_timestamp"},
        {
            "keys": [("timestamp", 1)],
            "name": "ix_ttl_30d",
            "expire_after_seconds": LOG_TTL_SECONDS,
        },
    ],
    "webhook_logs": [
        {"keys": [("timestamp", -1)], "name": "ix_timestamp_desc"},
        {"keys": [("user_id", 1), ("timestamp", -1)], "name": "ix_user_timestamp"},
        {"keys": [("mapping_id", 1), ("timestamp", -1)], "name": "ix_mapping_timestamp"},
        {"keys": [("success", 1), ("timestamp", -1)], "name": "ix_success_timestamp"},
        {
            "keys": [("timestamp", 1)],
            "name": "ix_ttl_30d",
            "expire_after_seconds": LOG_TTL_SECONDS,
        },
    ],
}


def _normalize_index_keys(key_info: Any) -> list[tuple[str, int]]:
    """Normalize Motor/pymongo index key metadata to a list of (field, direction)."""
    if not key_info:
        return []
    out: list[tuple[str, int]] = []
    for item in key_info:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            out.append((str(item[0]), int(item[1])))
        elif isinstance(item, dict):
            for field, direction in item.items():
                out.append((str(field), int(direction)))
    return out


async def _ensure_index(coll: Any, spec: dict[str, Any]) -> None:
    """Create an index, recreating timestamp TTL indexes when options differ."""
    keys = spec["keys"]
    name = spec["name"]
    expire = spec.get("expire_after_seconds")

    if expire is None:
        await coll.create_index(keys, name=name)
        logger.info("MongoDB index %s.%s ensured", coll.name, name)
        return

    desired_keys = list(keys)
    index_list = await coll.index_information()
    for idx_name, idx in index_list.items():
        if idx_name == "_id_":
            continue
        existing_keys = _normalize_index_keys(idx.get("key"))
        if existing_keys != desired_keys:
            continue
        existing_expire = idx.get("expireAfterSeconds")
        if idx_name == name and existing_expire == expire:
            logger.info("MongoDB TTL index %s.%s already correct", coll.name, name)
            return
        # Same key pattern but wrong name/options (e.g. legacy ix_timestamp without TTL).
        await coll.drop_index(idx_name)
        logger.info(
            "Dropped MongoDB index %s.%s to recreate as TTL (%ss)",
            coll.name,
            idx_name,
            expire,
        )

    await coll.create_index(keys, name=name, expireAfterSeconds=expire)
    logger.info("MongoDB TTL index %s.%s ensured (%ss)", coll.name, name, expire)


async def ensure_mongo_indexes() -> None:
    """Create indexes on MongoDB collections if they do not exist."""
    try:
        from app.db.mongo import get_mongo_db

        mongo_db = get_mongo_db()
        for coll_name, index_specs in INDEXES.items():
            coll = mongo_db[coll_name]
            for spec in index_specs:
                await _ensure_index(coll, spec)
    except Exception as e:
        logger.warning("MongoDB index creation skipped (Mongo may be unconfigured): %s", e)
