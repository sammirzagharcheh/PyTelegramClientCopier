"""Check that a bot can use source/dest chats before a mapping is saved."""

from __future__ import annotations

from typing import Any

from app.telegram.dialog_service import (
    AccountCredentials,
    SessionLockedError,
    entity_dialog_type,
    start_account_client,
)

_MEMBERSHIP_ERROR_NAMES = frozenset(
    {
        "UserNotParticipantError",
        "ChatAdminRequiredError",
        "ChannelPrivateError",
        "PeerIdInvalidError",
        "ChatWriteForbiddenError",
        "UserBannedInChannelError",
        "ChatForbiddenError",
    }
)


class PeerAccessDenied(Exception):
    """Bot cannot use this chat as mapped; API maps this to HTTP 400."""


def _is_membership_error(exc: BaseException) -> bool:
    return type(exc).__name__ in _MEMBERSHIP_ERROR_NAMES


async def _load_entity(client: Any, chat_id: int, label: str) -> Any:
    try:
        return await client.get_entity(chat_id)
    except SessionLockedError:
        raise
    except Exception as e:
        if _is_membership_error(e) or isinstance(e, ValueError):
            raise PeerAccessDenied(
                f"This bot cannot see the {label}. Add it to the chat first "
                "(channel: as admin; group: as a member with BotFather privacy disabled)."
            ) from e
        raise PeerAccessDenied(f"Could not look up the {label} for this bot.") from e


async def _permissions(client: Any, entity: Any, label: str) -> Any:
    try:
        return await client.get_permissions(entity)
    except SessionLockedError:
        raise
    except Exception as e:
        if _is_membership_error(e) or isinstance(e, ValueError):
            raise PeerAccessDenied(
                f"This bot is not a member of the {label}. Add it to the chat first."
            ) from e
        raise PeerAccessDenied(f"Could not check this bot's access to the {label}.") from e


def _assert_source(perms: Any, dialog_type: str) -> None:
    if getattr(perms, "is_banned", False):
        raise PeerAccessDenied("This bot is banned from the source chat.")
    if dialog_type == "channel" and not (
        getattr(perms, "is_admin", False) or getattr(perms, "is_creator", False)
    ):
        raise PeerAccessDenied(
            "This bot must be an admin on the source channel to receive posts."
        )


def _assert_dest(perms: Any, dialog_type: str) -> None:
    if getattr(perms, "is_banned", False):
        raise PeerAccessDenied("This bot is banned from the destination chat.")
    if getattr(perms, "is_creator", False):
        return
    if dialog_type == "channel":
        if not getattr(perms, "post_messages", False):
            raise PeerAccessDenied(
                "This bot cannot post in the destination channel. Grant it post permission."
            )
        return
    if getattr(perms, "send_messages", True) is False:
        raise PeerAccessDenied(
            "This bot cannot send messages in the destination chat."
        )


async def assert_bot_mapping_access(
    account: AccountCredentials,
    source_chat_id: int,
    dest_chat_id: int,
) -> None:
    """No-op for user accounts. Raises PeerAccessDenied if a bot cannot copy this route."""
    if account.account_type != "bot":
        return
    client = None
    try:
        client = await start_account_client(account)
        source_entity = await _load_entity(client, source_chat_id, "source chat")
        source_type = entity_dialog_type(source_entity)
        _assert_source(await _permissions(client, source_entity, "source chat"), source_type)

        dest_entity = await _load_entity(client, dest_chat_id, "destination chat")
        dest_type = entity_dialog_type(dest_entity)
        _assert_dest(await _permissions(client, dest_entity, "destination chat"), dest_type)
    except (SessionLockedError, PeerAccessDenied):
        raise
    except Exception as e:
        raise PeerAccessDenied(
            "Could not verify this bot's access to the source and destination chats."
        ) from e
    finally:
        if client is not None:
            try:
                await client.disconnect()
            except Exception:
                pass
