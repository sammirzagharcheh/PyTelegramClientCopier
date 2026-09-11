"""Unit tests for invite token helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.auth.invites import (
    generate_invite_token,
    hash_invite_token,
    invite_is_expired,
)


def test_hash_invite_token_stable():
    assert hash_invite_token("abc") == hash_invite_token("abc")
    assert hash_invite_token("abc") != hash_invite_token("abcd")


def test_generate_invite_token_unique():
    assert generate_invite_token() != generate_invite_token()


def test_invite_is_expired():
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    assert invite_is_expired(past) is True
    assert invite_is_expired(future) is False
