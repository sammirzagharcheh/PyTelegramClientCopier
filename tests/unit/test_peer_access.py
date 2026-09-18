"""Bot mapping access preflight (get_permissions)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.telegram.dialog_service import AccountCredentials
from app.telegram.peer_access import PeerAccessDenied, assert_bot_mapping_access


def _bot_account() -> AccountCredentials:
    return AccountCredentials(
        account_id=5,
        user_id=1,
        account_type="bot",
        session_path=None,
        bot_token="123456:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw",
        status="active",
    )


def _user_account() -> AccountCredentials:
    return AccountCredentials(
        account_id=1,
        user_id=1,
        account_type="user",
        session_path="/tmp/u.session",
        bot_token=None,
        status="active",
    )


def _perms(**kwargs):
    p = MagicMock()
    p.is_admin = kwargs.get("is_admin", False)
    p.is_creator = kwargs.get("is_creator", False)
    p.is_banned = kwargs.get("is_banned", False)
    p.post_messages = kwargs.get("post_messages", False)
    p.send_messages = kwargs.get("send_messages", False)
    return p


def _client(source_perms, dest_perms):
    client = MagicMock()
    client.get_entity = AsyncMock(side_effect=[MagicMock(), MagicMock()])
    client.get_permissions = AsyncMock(side_effect=[source_perms, dest_perms])
    client.disconnect = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_preflight_skips_user_accounts():
    with patch(
        "app.telegram.peer_access.start_account_client",
        new_callable=AsyncMock,
    ) as mock_start:
        await assert_bot_mapping_access(_user_account(), -1001, -1002)
    mock_start.assert_not_awaited()


@pytest.mark.asyncio
async def test_preflight_ok_admin_source_and_post_dest():
    client = _client(
        _perms(is_admin=True, post_messages=True),
        _perms(is_admin=True, post_messages=True),
    )
    with (
        patch(
            "app.telegram.peer_access.start_account_client",
            new_callable=AsyncMock,
            return_value=client,
        ),
        patch("app.telegram.peer_access.entity_dialog_type", side_effect=["channel", "channel"]),
    ):
        await assert_bot_mapping_access(_bot_account(), -1001, -1002)
    client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_preflight_source_channel_requires_admin():
    client = _client(
        _perms(is_admin=False, post_messages=False),
        _perms(is_admin=True, post_messages=True),
    )
    with (
        patch(
            "app.telegram.peer_access.start_account_client",
            new_callable=AsyncMock,
            return_value=client,
        ),
        patch("app.telegram.peer_access.entity_dialog_type", side_effect=["channel", "channel"]),
    ):
        with pytest.raises(PeerAccessDenied, match="admin on the source channel"):
            await assert_bot_mapping_access(_bot_account(), -1001, -1002)
    client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_preflight_dest_channel_requires_post():
    client = _client(
        _perms(is_admin=True, post_messages=True),
        _perms(is_admin=False, post_messages=False, send_messages=False),
    )
    with (
        patch(
            "app.telegram.peer_access.start_account_client",
            new_callable=AsyncMock,
            return_value=client,
        ),
        patch("app.telegram.peer_access.entity_dialog_type", side_effect=["channel", "channel"]),
    ):
        with pytest.raises(PeerAccessDenied, match="cannot post in the destination"):
            await assert_bot_mapping_access(_bot_account(), -1001, -1002)


@pytest.mark.asyncio
async def test_preflight_not_participant_is_denied():
    class UserNotParticipantError(Exception):
        pass

    client = MagicMock()
    client.get_entity = AsyncMock(return_value=MagicMock())
    client.get_permissions = AsyncMock(side_effect=UserNotParticipantError("not in chat"))
    client.disconnect = AsyncMock()

    with (
        patch(
            "app.telegram.peer_access.start_account_client",
            new_callable=AsyncMock,
            return_value=client,
        ),
        patch("app.telegram.peer_access.entity_dialog_type", return_value="group"),
    ):
        with pytest.raises(PeerAccessDenied, match="not a member of the source"):
            await assert_bot_mapping_access(_bot_account(), -1001, -1002)
    client.disconnect.assert_awaited_once()
