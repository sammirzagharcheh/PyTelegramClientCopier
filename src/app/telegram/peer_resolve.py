"""Resolve @username / t.me links / numeric IDs to Telegram peers."""

from __future__ import annotations

import re
from typing import Any

from telethon.utils import get_peer_id

from app.telegram.dialog_service import (
    AccountCredentials,
    SessionLockedError,
    TelegramDialog,
    TelegramDialogsError,
    entity_dialog_type,
    entity_username,
    start_account_client,
)


class InvalidPeerQuery(ValueError):
    """User-facing parse error for a chat query."""


_USERNAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{4,31}$")
_TME_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?(?:t\.me|telegram\.me|telegram\.dog)/(.+)$",
    re.IGNORECASE,
)


def parse_peer_query(raw: str) -> str | int:
    """Return a Telethon get_entity argument (username str or chat id int)."""
    q = (raw or "").strip()
    if not q:
        raise InvalidPeerQuery("Enter @username, t.me/username, or a numeric chat ID")

    if q.startswith("@"):
        q = q[1:].strip()

    m = _TME_RE.match(q)
    if m:
        rest = m.group(1).split("?")[0].strip("/")
        lower = rest.lower()
        if lower.startswith("joinchat/") or rest.startswith("+"):
            raise InvalidPeerQuery(
                "Invite links cannot be resolved; add the account to the chat "
                "and use @username or a numeric ID"
            )
        if lower.startswith("c/"):
            parts = rest.split("/")
            if len(parts) >= 2 and parts[1].isdigit():
                return int("-100" + parts[1])
            raise InvalidPeerQuery("Could not parse that t.me/c/ link")
        q = rest.split("/")[0]

    if q.lstrip("-").isdigit():
        n = int(q)
        if n == 0:
            raise InvalidPeerQuery("Chat ID must be non-zero")
        return n

    if not _USERNAME_RE.match(q):
        raise InvalidPeerQuery("Enter @username, t.me/username, or a numeric chat ID")
    return q


def _title_from_entity(entity: Any, chat_id: int) -> str:
    if getattr(entity, "title", None):
        return str(entity.title)
    first = getattr(entity, "first_name", None) or ""
    last = getattr(entity, "last_name", None) or ""
    combined = f"{first} {last}".strip()
    if combined:
        return combined
    username = entity_username(entity)
    if username:
        return username
    return f"Chat {chat_id}"


def entity_to_dialog(entity: Any) -> TelegramDialog:
    chat_id = int(get_peer_id(entity))
    return TelegramDialog(
        chat_id=chat_id,
        title=_title_from_entity(entity, chat_id),
        username=entity_username(entity),
        dialog_type=entity_dialog_type(entity),
    )


async def resolve_peer(account: AccountCredentials, query: str) -> TelegramDialog:
    """Look up a peer the account can see. Disconnects the client when done."""
    parsed = parse_peer_query(query)
    client = None
    try:
        client = await start_account_client(account)
        try:
            entity = await client.get_entity(parsed)
        except ValueError as e:
            raise TelegramDialogsError(str(e)) from e
        return entity_to_dialog(entity)
    except (SessionLockedError, ValueError, TelegramDialogsError):
        raise
    except Exception as e:
        raise TelegramDialogsError(str(e)) from e
    finally:
        if client is not None:
            try:
                await client.disconnect()
            except Exception:
                pass
