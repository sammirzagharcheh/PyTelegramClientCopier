"""Load Telegram dialogs for an account via Telethon."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from typing import Any

from telethon.tl.types import Channel, Chat, User

from app.telegram.client_manager import start_bot_client, start_user_client


class SessionLockedError(Exception):
    """SQLite session file locked (worker likely running)."""


class TelegramDialogsError(Exception):
    """Failed to load dialogs from Telegram."""


@dataclass(frozen=True)
class TelegramDialog:
    chat_id: int
    title: str
    username: str | None
    dialog_type: str


@dataclass(frozen=True)
class AccountCredentials:
    account_id: int
    user_id: int
    account_type: str
    session_path: str | None
    bot_token: str | None
    status: str


_CACHE: dict[tuple[int, int], tuple[float, list[TelegramDialog]]] = {}
_CACHE_TTL_SEC = 90.0


def clear_dialog_cache() -> None:
    """Clear in-process dialog cache (for tests)."""
    _CACHE.clear()


def _entity_dialog_type(entity: Any) -> str:
    if isinstance(entity, User):
        return "bot" if getattr(entity, "bot", False) else "user"
    if isinstance(entity, Channel):
        if getattr(entity, "broadcast", False):
            return "channel"
        return "group"
    if isinstance(entity, Chat):
        return "group"
    return "unknown"


def _dialog_title(dialog: Any) -> str:
    name = getattr(dialog, "name", None) or getattr(dialog, "title", None)
    if name:
        return str(name)
    entity = dialog.entity
    if isinstance(entity, User):
        first = getattr(entity, "first_name", None) or ""
        last = getattr(entity, "last_name", None) or ""
        combined = f"{first} {last}".strip()
        if combined:
            return combined
        return getattr(entity, "username", None) or f"User {entity.id}"
    return getattr(entity, "title", None) or f"Chat {dialog.id}"


def _entity_username(entity: Any) -> str | None:
    username = getattr(entity, "username", None)
    return str(username) if username else None


async def list_account_dialogs(
    account: AccountCredentials,
    *,
    limit: int = 500,
    use_cache: bool = True,
) -> list[TelegramDialog]:
    """Fetch dialogs for a Telegram account. Disconnects client when done."""
    if account.status != "active":
        raise ValueError("Account must be active")

    cache_key = (account.account_id, account.user_id)
    if use_cache:
        cached = _CACHE.get(cache_key)
        if cached and cached[0] > time.monotonic():
            return list(cached[1])

    limit = min(max(1, limit), 500)
    client = None
    try:
        if account.account_type == "user":
            if not account.session_path:
                raise ValueError("Account is not connected")
            try:
                client = await start_user_client(account.session_path)
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower():
                    raise SessionLockedError(str(e)) from e
                raise TelegramDialogsError(str(e)) from e
        elif account.account_type == "bot":
            if not account.bot_token:
                raise ValueError("Account is not connected")
            client = await start_bot_client(account.bot_token)
        else:
            raise ValueError(f"Unsupported account type: {account.account_type}")

        items: list[TelegramDialog] = []
        async for dialog in client.iter_dialogs(limit=limit):
            entity = dialog.entity
            items.append(
                TelegramDialog(
                    chat_id=int(dialog.id),
                    title=_dialog_title(dialog),
                    username=_entity_username(entity),
                    dialog_type=_entity_dialog_type(entity),
                )
            )
        if use_cache:
            _CACHE[cache_key] = (time.monotonic() + _CACHE_TTL_SEC, items)
        return items
    except (SessionLockedError, ValueError):
        raise
    except Exception as e:
        raise TelegramDialogsError(str(e)) from e
    finally:
        if client is not None:
            try:
                await client.disconnect()
            except Exception:
                pass
