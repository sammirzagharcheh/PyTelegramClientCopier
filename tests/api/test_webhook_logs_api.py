"""API tests for /api/webhook-logs user/admin access and response fields."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch


class _MockCursor:
    def __init__(self, docs: list[dict]) -> None:
        self._docs = docs
        self._offset = 0
        self._limit = len(docs)

    def sort(self, key: str, direction: int):
        reverse = direction < 0
        self._docs = sorted(self._docs, key=lambda d: d.get(key), reverse=reverse)
        return self

    def skip(self, offset: int):
        self._offset = max(0, int(offset))
        return self

    def limit(self, limit: int):
        self._limit = max(0, int(limit))
        return self

    def __aiter__(self):
        sliced = self._docs[self._offset : self._offset + self._limit]

        async def _gen():
            for d in sliced:
                yield d

        return _gen()


class _MockWebhookLogsCollection:
    def __init__(self, docs: list[dict]) -> None:
        self._docs = docs

    @staticmethod
    def _matches(doc: dict, match: dict) -> bool:
        mapping_filter = (match.get("mapping_id") or {}).get("$in")
        if mapping_filter is not None and doc.get("mapping_id") not in mapping_filter:
            return False
        if "success" in match and bool(doc.get("success")) != bool(match["success"]):
            return False
        ts_match = match.get("timestamp") or {}
        ts = doc.get("timestamp")
        if "$gte" in ts_match and ts < ts_match["$gte"]:
            return False
        if "$lte" in ts_match and ts > ts_match["$lte"]:
            return False
        return True

    def _filtered(self, match: dict) -> list[dict]:
        return [d for d in self._docs if self._matches(d, match)]

    async def count_documents(self, match: dict) -> int:
        return len(self._filtered(match))

    def find(self, match: dict):
        return _MockCursor(self._filtered(match))


class _MockMongoDb:
    def __init__(self, docs: list[dict]) -> None:
        self.webhook_logs = _MockWebhookLogsCollection(docs)


def _sample_docs() -> list[dict]:
    now = datetime.now(timezone.utc)
    return [
        {
            "timestamp": now,
            "user_id": 1,
            "mapping_id": 1,
            "source_chat_id": 10,
            "dest_chat_id": 20,
            "event": "message_copied",
            "request": {
                "url": "https://example.com/hook",
                "method": "POST",
                "payload_size_bytes": 128,
                "body_preview": '{"event":"message_copied","mapping_id":1}',
            },
            "response": {
                "status_code": 200,
                "status_text": "OK",
                "latency_ms": 44,
                "content_type": "application/json",
                "body": '{"ok":true}',
                "body_truncated": False,
            },
            "success": True,
            "error": None,
        },
        {
            "timestamp": now - timedelta(seconds=2),
            "user_id": 3,
            "mapping_id": 2,
            "source_chat_id": 30,
            "dest_chat_id": 40,
            "event": "message_copied",
            "request": {
                "url": "https://other.example/hook",
                "method": "POST",
                "payload_size_bytes": 64,
                "body_preview": '{"event":"message_copied","mapping_id":2}',
            },
            "response": {
                "status_code": 500,
                "status_text": "Internal Server Error",
                "latency_ms": 70,
                "content_type": "application/json",
                "body": '{"error":"failed"}',
                "body_truncated": False,
            },
            "success": False,
            "error": "HTTP 500",
        },
    ]


def test_webhook_logs_401_no_auth(api_client):
    r = api_client.get("/api/webhook-logs")
    assert r.status_code == 401


def test_webhook_logs_user_scope_and_response_fields(api_client, user_token):
    mock_db = _MockMongoDb(_sample_docs())
    with patch("app.web.routers.webhook_logs.get_mongo_db", return_value=mock_db):
        r = api_client.get(
            "/api/webhook-logs?user_id=3",
            headers={"Authorization": f"Bearer {user_token}"},
        )

    assert r.status_code == 200
    data = r.json()
    assert isinstance(data["items"], list)
    assert data["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["mapping_id"] == 1  # user token must stay scoped to own mappings
    assert item["request_body_preview"]
    assert item["status_text"] == "OK"
    assert item["response_content_type"] == "application/json"
    assert item["response_body"] == '{"ok":true}'
    assert item["response_body_truncated"] is False


def test_webhook_logs_admin_can_filter_user(api_client, admin_token):
    mock_db = _MockMongoDb(_sample_docs())
    with patch("app.web.routers.webhook_logs.get_mongo_db", return_value=mock_db):
        r = api_client.get(
            "/api/webhook-logs?user_id=3",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["mapping_id"] == 2
