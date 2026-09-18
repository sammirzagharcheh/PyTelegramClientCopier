"""Validate Telegram bot tokens (BotFather shape)."""

from __future__ import annotations

import re

# BotFather tokens look like: <bot_id>:<secret> (secret is typically 35 chars).
_BOT_TOKEN_RE = re.compile(r"^\d{5,}:[A-Za-z0-9_-]{20,}$")


def normalize_bot_token(token: str) -> str:
    return token.strip()


def is_valid_bot_token(token: str | None) -> bool:
    if not token:
        return False
    return bool(_BOT_TOKEN_RE.match(normalize_bot_token(token)))
