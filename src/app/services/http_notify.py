"""Async HTTP POST helpers for webhooks (copy notifications, health alerts)."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def post_json_webhook(url: str, secret: str | None, payload: dict[str, Any]) -> None:
    """POST JSON body; optional HMAC-SHA256 hex in X-Tgc-Signature when secret is set."""
    import httpx

    body = json.dumps(payload, default=str).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if secret:
        sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        headers["X-Tgc-Signature"] = sig
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(url, content=body, headers=headers)
            r.raise_for_status()
    except Exception as e:
        logger.warning("Webhook POST failed url=%s err=%s", url, e)
