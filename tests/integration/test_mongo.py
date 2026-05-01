"""Integration tests for MongoDB connection and read/write."""

from __future__ import annotations

import pytest
from pymongo.errors import PyMongoError

from app.db.mongo import get_mongo_db

# Collection used only for tests; safe to write/delete
TEST_COLLECTION = "_connection_test"


@pytest.mark.asyncio
async def test_mongo_ping():
    """Test MongoDB connection via ping."""
    db = get_mongo_db()
    try:
        result = await db.command("ping")
    except PyMongoError as e:
        pytest.skip(f"MongoDB not available: {e}")
    assert result.get("ok") == 1.0


@pytest.mark.asyncio
async def test_mongo_write_read_delete():
    """Test MongoDB write, read, and delete."""
    db = get_mongo_db()
    col = db[TEST_COLLECTION]

    doc = {"_test": True, "source": "pytest", "value": 42}
    try:
        insert_result = await col.insert_one(doc)
    except PyMongoError as e:
        pytest.skip(f"MongoDB not available: {e}")
    assert insert_result.inserted_id is not None

    try:
        found = await col.find_one({"_id": insert_result.inserted_id})
        assert found is not None
        assert found["_test"] is True
        assert found["value"] == 42

        delete_result = await col.delete_one({"_id": insert_result.inserted_id})
        assert delete_result.deleted_count == 1

        gone = await col.find_one({"_id": insert_result.inserted_id})
        assert gone is None
    finally:
        await col.delete_many({"_test": True})
