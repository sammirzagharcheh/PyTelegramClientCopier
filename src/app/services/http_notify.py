"""Async HTTP POST helpers for webhooks (copy notifications, health alerts)."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
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
) -> None:
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
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(url, content=body, headers=headers)
            r.raise_for_status()
    except Exception as e:
        logger.warning("Webhook POST failed url=%s err=%s", url, e)
