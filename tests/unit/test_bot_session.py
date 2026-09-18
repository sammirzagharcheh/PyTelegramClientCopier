"""Bot StringSession path load/save."""

from cryptography.fernet import Fernet

from app.telegram.at_rest import SEAL_PREFIX, reveal_secret
from app.telegram.bot_session import (
    bot_session_path,
    load_bot_string_session,
    save_bot_string_session,
)

_SESSION_BLOB = "1A" + "B" * 80


def test_bot_session_path_layout(monkeypatch, tmp_path):
    monkeypatch.setattr("app.telegram.bot_session.settings.sessions_dir", str(tmp_path))
    p = bot_session_path(7, 12)
    assert p == tmp_path / "7" / "12.bot.session"


def test_save_and_load_plain(monkeypatch, tmp_path):
    monkeypatch.setattr("app.telegram.at_rest.settings.credentials_at_rest_key", "")
    path = tmp_path / "1" / "2.bot.session"
    save_bot_string_session(path, _SESSION_BLOB)
    assert path.read_text(encoding="utf-8") == _SESSION_BLOB
    assert reveal_secret(path.read_text(encoding="utf-8").strip()) == _SESSION_BLOB
    assert load_bot_string_session(tmp_path / "missing.bot.session").save() == ""


def test_save_and_load_sealed(monkeypatch, tmp_path):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setattr("app.telegram.at_rest.settings.credentials_at_rest_key", key)
    path = tmp_path / "a.bot.session"
    save_bot_string_session(path, _SESSION_BLOB)
    raw = path.read_text(encoding="utf-8")
    assert raw.startswith(SEAL_PREFIX)
    assert _SESSION_BLOB not in raw
    assert reveal_secret(raw.strip()) == _SESSION_BLOB
