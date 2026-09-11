"""Unit tests for API key scope catalog helpers."""

from __future__ import annotations

import pytest

from app.auth.scopes import (
    API_KEY_SCOPES,
    ensure_api_key_scopes,
    has_any_scope,
    parse_scopes,
    validate_scopes,
    validate_scopes_string,
)


def test_parse_scopes_dedupes_and_strips():
    assert parse_scopes(" mappings:read , mappings:write,mappings:read ") == [
        "mappings:read",
        "mappings:write",
    ]
    assert parse_scopes("") == []
    assert parse_scopes(None) == []


def test_validate_scopes_rejects_unknown():
    with pytest.raises(ValueError, match="Unknown"):
        validate_scopes("mappings:read,admin:all")


def test_validate_scopes_requires_at_least_one():
    with pytest.raises(ValueError, match="At least one"):
        validate_scopes("  ,  ")


def test_validate_scopes_string_roundtrip():
    assert validate_scopes_string("mappings:write, mappings:read") == "mappings:write,mappings:read"
    assert set(validate_scopes_string("logs:read").split(",")) <= API_KEY_SCOPES


def test_has_any_scope():
    assert has_any_scope(["mappings:read"], ["mappings:read", "mappings:write"])
    assert not has_any_scope(["mappings:read"], ["workers:write"])
    assert has_any_scope(["a"], [])


def test_ensure_api_key_scopes_noop_for_jwt():
    ensure_api_key_scopes({"auth_via": "jwt"}, ["mappings:write"])


def test_ensure_api_key_scopes_enforces_for_api_key():
    user = {"auth_via": "api_key", "api_key_scopes": ["mappings:read"]}
    ensure_api_key_scopes(user, ["mappings:read"])
    with pytest.raises(PermissionError, match="missing required scope"):
        ensure_api_key_scopes(user, ["mappings:write"])
