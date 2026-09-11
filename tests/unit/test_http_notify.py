from __future__ import annotations

import json

import pytest

from app.services.http_notify import post_json_webhook


class _DummyResponse:
    status_code = 200
    reason_phrase = "OK"
    text = '{"ok":true}'
    headers = {"content-type": "application/json"}

    def raise_for_status(self) -> None:
        return None


class _DummyClient:
    def __init__(self, recorder: list[dict]) -> None:
        self._recorder = recorder

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url: str, content: bytes, headers: dict[str, str]):
        self._recorder.append({"url": url, "content": content, "headers": headers})
        return _DummyResponse()


@pytest.mark.asyncio
async def test_post_json_webhook_custom_header_value_mode(monkeypatch):
    calls: list[dict] = []

    def _factory(*args, **kwargs):
        return _DummyClient(calls)

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", _factory)
    result = await post_json_webhook(
        "https://example.com/hook",
        secret=None,
        payload={"ok": True},
        secret_mode="header_value",
        secret_header_name="X-Custom-Secret",
        secret_header_value="abc123",
    )
    assert calls
    assert calls[0]["headers"]["X-Custom-Secret"] == "abc123"
    assert json.loads(calls[0]["content"].decode("utf-8")) == {"ok": True}
    assert result["request_headers"]["Content-Type"] == "application/json"
    assert result["request_headers"]["X-Custom-Secret"] == "***"


@pytest.mark.asyncio
async def test_post_json_webhook_hmac_mode_respects_custom_header_name(monkeypatch):
    calls: list[dict] = []

    def _factory(*args, **kwargs):
        return _DummyClient(calls)

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", _factory)
    result = await post_json_webhook(
        "https://example.com/hook",
        secret="topsecret",
        payload={"x": 1},
        secret_mode="hmac_sha256",
        secret_header_name="X-Hmac",
        secret_header_value="custom-value",
    )
    assert calls
    assert calls[0]["headers"]["X-Tgc-Signature"]
    assert calls[0]["headers"]["X-Hmac"] == "custom-value"
    assert result["request_headers"]["X-Hmac"] == "***"
    assert result["request_headers"]["X-Tgc-Signature"] == "***"

