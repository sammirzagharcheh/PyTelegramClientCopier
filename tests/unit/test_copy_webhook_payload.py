from __future__ import annotations

import pytest

from app.services.mapping_service import ChannelMapping
from app.telegram.handlers import _fire_copy_webhook


@pytest.mark.asyncio
async def test_fire_copy_webhook_renders_dynamic_payload_and_custom_secret_header(monkeypatch):
    mapping = ChannelMapping(
        id=7,
        user_id=1,
        source_chat_id=10,
        dest_chat_id=20,
        enabled=True,
        filters=[],
        source_chat_title=None,
        dest_chat_title=None,
        copy_webhook_url="https://example.com/hook",
        copy_webhook_payload_template='{"kind":"{{event}}","src":"{{source_msg_id}}","dst":"{{dest_msg_id}}"}',
        copy_webhook_secret_header_name="X-Webhook-Secret",
        copy_webhook_secret_header_value="my-secret",
        copy_webhook_secret_mode="header_value",
    )
    captured: dict = {}
    inserted: dict = {}

    async def _fake_post(url, secret, payload, **kwargs):
        captured["url"] = url
        captured["secret"] = secret
        captured["payload"] = payload
        captured["kwargs"] = kwargs
        return {
            "success": True,
            "status_code": 200,
            "response_body": "ok",
            "error": None,
            "latency_ms": 12,
            "payload_size_bytes": 123,
            "request_body_preview": '{"kind":"message_copied"}',
            "request_headers": {
                "Content-Type": "application/json",
                "X-API-Key": "***",
            },
        }

    class _WebhookLogCollection:
        async def insert_one(self, doc):
            inserted.update(doc)

    class _MongoDb:
        webhook_logs = _WebhookLogCollection()

    import app.services.http_notify as hn

    monkeypatch.setattr(hn, "post_json_webhook", _fake_post)
    await _fire_copy_webhook(
        mapping,
        {
            "event": "message_copied",
            "source_msg_id": 123,
            "dest_msg_id": 456,
            "source_chat_id": 10,
            "dest_chat_id": 20,
            "mapping_id": 7,
            "user_id": 1,
        },
        _MongoDb(),
    )
    assert captured["url"] == "https://example.com/hook"
    assert captured["payload"] == {"kind": "message_copied", "src": "123", "dst": "456"}
    assert captured["kwargs"]["secret_mode"] == "header_value"
    assert captured["kwargs"]["secret_header_name"] == "X-Webhook-Secret"
    assert captured["kwargs"]["secret_header_value"] == "my-secret"
    assert inserted["mapping_id"] == 7
    assert inserted["success"] is True
    assert inserted["request"]["body_preview"] == '{"kind":"message_copied"}'
    assert inserted["request"]["headers"]["X-API-Key"] == "***"

