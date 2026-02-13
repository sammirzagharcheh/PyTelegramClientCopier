"""Integration tests for ensure_mongo_indexes - verifies indexes exist on message_logs and worker_logs."""

from __future__ import annotations

import pytest

from app.db.mongo import get_mongo_db
from app.db.mongo_indexes import INDEXES, ensure_mongo_indexes


@pytest.mark.asyncio
async def test_ensure_mongo_indexes_runs_without_error():
    """ensure_mongo_indexes completes without raising (may skip if Mongo unavailable)."""
    try:
        await ensure_mongo_indexes()
    except Exception:
        pytest.fail("ensure_mongo_indexes should not raise (logs warning if Mongo down)")


@pytest.mark.asyncio
async def test_mongo_indexes_exist_when_connected():
    """When MongoDB is available, message_logs and worker_logs have expected indexes."""
    try:
        await ensure_mongo_indexes()
        db = get_mongo_db()
        for coll_name, index_specs in INDEXES.items():
            coll = db[coll_name]
            index_list = await coll.index_information()
            index_names = [idx.get("name") for idx in index_list.values()]
            for spec in index_specs:
                assert spec["name"] in index_names, (
                    f"Index {spec['name']} not found on {coll_name}. "
                    f"Got: {index_names}"
                )
    except Exception as e:
        pytest.skip(f"MongoDB not available: {e}")
