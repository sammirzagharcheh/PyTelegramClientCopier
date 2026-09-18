"""Fernet seal/reveal for bot credentials."""

import pytest
from cryptography.fernet import Fernet

from app.telegram.at_rest import (
    SEAL_PREFIX,
    CredentialSealError,
    reveal_secret,
    seal_secret,
)


def test_passthrough_without_key(monkeypatch):
    monkeypatch.setattr("app.telegram.at_rest.settings.credentials_at_rest_key", "")
    assert seal_secret("123456:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw") == (
        "123456:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"
    )
    assert reveal_secret("plain") == "plain"
    assert reveal_secret(None) == ""


def test_roundtrip_with_key(monkeypatch):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setattr("app.telegram.at_rest.settings.credentials_at_rest_key", key)
    sealed = seal_secret("123456:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw")
    assert sealed.startswith(SEAL_PREFIX)
    assert "123456:" not in sealed
    assert reveal_secret(sealed) == "123456:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"


def test_encrypted_without_key_errors(monkeypatch):
    monkeypatch.setattr("app.telegram.at_rest.settings.credentials_at_rest_key", "")
    with pytest.raises(CredentialSealError, match="CREDENTIALS_AT_REST_KEY"):
        reveal_secret(f"{SEAL_PREFIX}not-a-real-token")


def test_wrong_key_errors(monkeypatch):
    key1 = Fernet.generate_key().decode("ascii")
    key2 = Fernet.generate_key().decode("ascii")
    monkeypatch.setattr("app.telegram.at_rest.settings.credentials_at_rest_key", key1)
    sealed = seal_secret("123456:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw")
    monkeypatch.setattr("app.telegram.at_rest.settings.credentials_at_rest_key", key2)
    with pytest.raises(CredentialSealError, match="CREDENTIALS_AT_REST_KEY"):
        reveal_secret(sealed)
