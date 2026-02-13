"""Ensure MongoDB indexes exist for message_logs and worker_logs collections."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

INDEXES = {
    "message_logs": [
        {"keys": [("user_id", 1), ("timestamp", -1)], "name": "ix_user_timestamp"},
        {"keys": [("timestamp", 1)], "name": "ix_timestamp"},
    ],
    "worker_logs": [
        {"keys": [("user_id", 1), ("timestamp", -1)], "name": "ix_user_timestamp"},
        {"keys": [("timestamp", 1)], "name": "ix_timestamp"},
    ],
}


async def ensure_mongo_indexes() -> None:
    """Create indexes on MongoDB collections if they do not exist."""
    try:
        from app.db.mongo import get_mongo_db

        mongo_db = get_mongo_db()
        for coll_name, index_specs in INDEXES.items():
            coll = mongo_db[coll_name]
            for spec in index_specs:
                await coll.create_index(spec["keys"], name=spec["name"])
                logger.info("MongoDB index %s.%s ensured", coll_name, spec["name"])
    except Exception as e:
        logger.warning("MongoDB index creation skipped (Mongo may be unconfigured): %s", e)
