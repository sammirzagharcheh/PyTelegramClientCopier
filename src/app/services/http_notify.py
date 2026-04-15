"""Async HTTP POST helpers for webhooks (copy notifications, health alerts)."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


async def post_json_webhook(
    url: str,
    secret: str | None,
    payload: dict[str, Any],
    *,
    secret_mode: str = "hmac_sha256",
    secret_header_name: str | None = None,
    secret_header_value: str | None = None,
) -> dict[str, Any]:
    """POST JSON body with configurable secret handling.

    Modes:
    - hmac_sha256: sign body using `secret` and send hex signature in header.
    - header_value: send `secret_header_value` as custom header.
    - none: do not attach secret-related header.
    """
    import httpx

    body = json.dumps(payload, default=str).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if secret_mode == "hmac_sha256" and secret:
        sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        headers[(secret_header_name or "X-Tgc-Signature").strip()] = sig
    elif secret_mode == "header_value" and secret_header_name and secret_header_value:
        headers[secret_header_name.strip()] = str(secret_header_value)
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, content=body, headers=headers)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        response_body = (response.text or "")[:2000]
        success = 200 <= int(response.status_code) < 300
        if not success:
            logger.warning(
                "Webhook POST failed url=%s status=%s body=%s",
                url,
                response.status_code,
                response_body,
            )
        return {
            "success": success,
            "status_code": int(response.status_code),
            "response_body": response_body,
            "error": None if success else f"HTTP {response.status_code}",
            "latency_ms": elapsed_ms,
            "payload_size_bytes": len(body),
        }
    except Exception as e:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.warning("Webhook POST failed url=%s err=%s", url, e)
        return {
            "success": False,
            "status_code": None,
            "response_body": None,
            "error": str(e),
            "latency_ms": elapsed_ms,
            "payload_size_bytes": len(body),
        }
