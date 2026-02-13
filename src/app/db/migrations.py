"""SQLite schema migrations."""

from __future__ import annotations

import hashlib
import logging

import aiosqlite

logger = logging.getLogger(__name__)

MIGRATIONS = [
    # v1: base schema (handled by sqlite.py SCHEMA_SQL)
    None,
    # v2: add auth and metadata columns
    """
    ALTER TABLE users ADD COLUMN password_hash TEXT;
    ALTER TABLE users ADD COLUMN name TEXT;
    ALTER TABLE users ADD COLUMN updated_at TEXT;
    """,
    # v3: add telegram_accounts columns
    """
    ALTER TABLE telegram_accounts ADD COLUMN name TEXT;
    ALTER TABLE telegram_accounts ADD COLUMN created_at TEXT;
    """,
    # v4: add channel_mappings columns
    """
    ALTER TABLE channel_mappings ADD COLUMN name TEXT;
    ALTER TABLE channel_mappings ADD COLUMN source_chat_title TEXT;
    ALTER TABLE channel_mappings ADD COLUMN dest_chat_title TEXT;
    ALTER TABLE channel_mappings ADD COLUMN created_at TEXT;
    ALTER TABLE channel_mappings ADD COLUMN telegram_account_id INTEGER REFERENCES telegram_accounts(id);
    """,
    # v5: refresh_tokens table
    """
    CREATE TABLE IF NOT EXISTS refresh_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token_hash TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    CREATE INDEX IF NOT EXISTS ix_refresh_tokens_token_hash ON refresh_tokens(token_hash);
    """,
    # v6: admin_invites table
    """
    CREATE TABLE IF NOT EXISTS admin_invites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        token TEXT NOT NULL UNIQUE,
        created_by INTEGER NOT NULL,
        expires_at TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(created_by) REFERENCES users(id)
    );
    """,
    # v7: app_settings table (MongoDB URI, etc.)
    """
    CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
    # v8: login_sessions table for Telethon login wizard
    """
    CREATE TABLE IF NOT EXISTS login_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        phone TEXT NOT NULL,
        tmp_session_name TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """,
    # v9: add phone_code_hash to login_sessions
    """
    ALTER TABLE login_sessions ADD COLUMN phone_code_hash TEXT;
    """,
    # v10: worker_registry for persistent worker tracking across API restarts
    """
    CREATE TABLE IF NOT EXISTS worker_registry (
        worker_id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        account_id INTEGER NOT NULL,
        session_path TEXT NOT NULL,
        pid INTEGER NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
    # v11: performance indexes for common query patterns
    """
    CREATE INDEX IF NOT EXISTS ix_users_id_status ON users(id, status);
    CREATE INDEX IF NOT EXISTS ix_telegram_accounts_user_id ON telegram_accounts(user_id);
    CREATE INDEX IF NOT EXISTS ix_telegram_accounts_user_status ON telegram_accounts(user_id, status);
    CREATE INDEX IF NOT EXISTS ix_channel_mappings_user_id ON channel_mappings(user_id);
    CREATE INDEX IF NOT EXISTS ix_channel_mappings_user_src_dest ON channel_mappings(user_id, source_chat_id, dest_chat_id);
    CREATE INDEX IF NOT EXISTS ix_mapping_filters_mapping_id ON mapping_filters(mapping_id);
    CREATE INDEX IF NOT EXISTS ix_dest_message_index_user_id ON dest_message_index(user_id);
    """,
]


def _migration_hash(sql: str | None) -> str:
    if sql is None:
        return "v1_base"
    return hashlib.sha256(sql.strip().encode()).hexdigest()[:16]


async def ensure_migrations_table(db: aiosqlite.Connection) -> None:
    await db.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await db.commit()


async def get_applied_migrations(db: aiosqlite.Connection) -> set[str]:
    await ensure_migrations_table(db)
    async with db.execute("SELECT name FROM _migrations") as cur:
        rows = await cur.fetchall()
    return {r[0] for r in rows}


async def run_migrations(db: aiosqlite.Connection) -> None:
    applied = await get_applied_migrations(db)
    for i, sql in enumerate(MIGRATIONS):
        if i == 0:
            continue
        name = f"m{i}_{_migration_hash(sql)}"
        if name in applied:
            continue
        for stmt in sql.strip().split(";"):
            stmt = stmt.strip()
            if not stmt:
                continue
            try:
                await db.execute(stmt)
            except aiosqlite.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    logger.info("Column already exists, skipping: %s", stmt[:50])
                else:
                    raise
        await db.execute(
            "INSERT INTO _migrations (id, name) VALUES (?, ?)",
            (i, name),
        )
        await db.commit()
        logger.info("Applied migration: %s", name)
