"""On-disk StringSession for bot accounts (not Telethon sqlite)."""

from __future__ import annotations

import os
from pathlib import Path

from telethon.sessions import StringSession

from app.config import settings
from app.telegram.at_rest import reveal_secret, seal_secret


def bot_session_path(user_id: int, account_id: int) -> Path:
    return Path(settings.sessions_dir) / str(user_id) / f"{account_id}.bot.session"


def load_bot_string_session(path: str | Path) -> StringSession:
    p = Path(path)
    if not p.is_file():
        return StringSession()
    raw = p.read_text(encoding="utf-8").strip()
    if not raw:
        return StringSession()
    return StringSession(reveal_secret(raw))


def save_bot_string_session(path: str | Path, session_str: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(seal_secret(session_str), encoding="utf-8")
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass
