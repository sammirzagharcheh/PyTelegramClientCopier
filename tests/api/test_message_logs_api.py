"""API tests for /api/message-logs, including batch title fallback."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.sqlite import get_sqlite


@pytest.fixture
def api_client_with_mapping_titles(api_client, tmp_path):
    """API client with channel_mappings that have source/dest titles for fallback test."""
    from app.config import settings

    settings.sqlite_path = str(tmp_path / "test.db")

    async def update():
        db = await get_sqlite()
        await db.execute(
            "UPDATE channel_mappings SET source_chat_title = ?, dest_chat_title = ? "
            "WHERE user_id = 1 AND source_chat_id = 10 AND dest_chat_id = 20",
            ("Source Channel", "Dest Channel"),
        )
        await db.commit()
        await db.close()

    import asyncio
    asyncio.run(update())
    return api_client


def test_message_logs_401_no_auth(api_client):
    """Message logs returns 401 when not authenticated."""
    r = api_client.get("/api/message-logs")
    assert r.status_code == 401


def test_message_logs_200_empty_schema(api_client, user_token):
    """Message logs returns 200 and expected schema when Mongo returns empty (mocked)."""
    def mock_aggregate(pipeline):
        has_count = any(
            isinstance(s, dict) and s.get("$count") == "total"
            for s in pipeline
        )
        if has_count:
            async def count_gen():
                yield {"total": 0}
            return count_gen()
        async def list_gen():
            if False:
                yield
        return list_gen()

    mock_coll = AsyncMock()
    mock_coll.aggregate = mock_aggregate
    mock_coll.count_documents = AsyncMock(return_value=0)

    mock_db = AsyncMock()
    mock_db.message_logs = mock_coll

    def mock_get_mongo_db():
        return mock_db

    with patch("app.web.routers.message_logs.get_mongo_db", side_effect=mock_get_mongo_db):
        r = api_client.get(
            "/api/message-logs",
            headers={"Authorization": f"Bearer {user_token}"},
        )
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data
    assert isinstance(data["items"], list)
    assert data["total"] == 0
    assert data["items"] == []


def test_message_logs_batch_title_fallback(
    api_client_with_mapping_titles, user_token
):
    """When Mongo docs lack titles, batch SQLite lookup fills source_chat_title and dest_chat_title."""
    client: TestClient = api_client_with_mapping_titles
    ts = datetime.now(timezone.utc)

    # Mongo doc has no source_chat_title/dest_chat_title; matches mapping (1, 10, 20)
    docs = [
        {
            "user_id": 1,
            "source_chat_id": 10,
            "dest_chat_id": 20,
            "source_msg_id": 100,
            "dest_msg_id": 200,
            "source_chat_title": None,
            "dest_chat_title": None,
            "timestamp": ts,
            "status": "ok",
        }
    ]

    def mock_aggregate(pipeline):
        has_count = any(
            isinstance(s, dict) and s.get("$count") == "total"
            for s in pipeline
        )
        if has_count:
            async def count_gen():
                yield {"total": 1}
            return count_gen()
        async def list_gen():
            for d in docs:
                yield d
        return list_gen()

    mock_coll = AsyncMock()
    mock_coll.aggregate = mock_aggregate
    mock_coll.count_documents = AsyncMock(return_value=1)

    mock_db = AsyncMock()
    mock_db.message_logs = mock_coll

    def mock_get_mongo_db():
        return mock_db

    with patch("app.web.routers.message_logs.get_mongo_db", side_effect=mock_get_mongo_db):
        r = client.get(
            "/api/message-logs",
            headers={"Authorization": f"Bearer {user_token}"},
        )
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["user_id"] == 1
    assert item["source_chat_id"] == 10
    assert item["dest_chat_id"] == 20
    # Batch fallback should have filled titles from channel_mappings
    assert item["source_chat_title"] == "Source Channel"
    assert item["dest_chat_title"] == "Dest Channel"
