from __future__ import annotations

from pathlib import Path

import aiosqlite

from app.config import settings


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT UNIQUE NOT NULL,
  role TEXT NOT NULL DEFAULT 'user',
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS telegram_accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  type TEXT NOT NULL,
  session_path TEXT,
  phone TEXT,
  bot_token TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS channel_mappings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  source_chat_id INTEGER NOT NULL,
  dest_chat_id INTEGER NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS mapping_filters (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  mapping_id INTEGER NOT NULL,
  include_text TEXT,
  exclude_text TEXT,
  media_types TEXT,
  regex_pattern TEXT,
  FOREIGN KEY(mapping_id) REFERENCES channel_mappings(id)
);

CREATE TABLE IF NOT EXISTS dest_message_index (
  user_id INTEGER NOT NULL,
  source_chat_id INTEGER NOT NULL,
  source_msg_id INTEGER NOT NULL,
  dest_chat_id INTEGER NOT NULL,
  dest_msg_id INTEGER NOT NULL,
  PRIMARY KEY (user_id, source_chat_id, source_msg_id, dest_chat_id)
);
"""


async def init_sqlite() -> None:
    db_path = Path(settings.sqlite_path)
    if db_path.parent:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(settings.sqlite_path) as db:
        await db.executescript(SCHEMA_SQL)
        await db.commit()
        from app.db.migrations import run_migrations

        await run_migrations(db)


async def get_sqlite() -> aiosqlite.Connection:
    return await aiosqlite.connect(settings.sqlite_path)

