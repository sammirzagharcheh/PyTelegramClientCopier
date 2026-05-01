from __future__ import annotations

import re
import random
import asyncio
import logging
from collections.abc import Iterable, Sequence
from datetime import datetime, timezone
from typing import Any

import aiosqlite
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError as SAIntegrityError
from sqlalchemy.exc import OperationalError as SAOperationalError
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from app.config import settings

logger = logging.getLogger(__name__)

POSTGRES_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
  id BIGSERIAL PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  role TEXT NOT NULL DEFAULT 'user',
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  password_hash TEXT,
  name TEXT,
  updated_at TEXT,
  timezone TEXT
);

CREATE TABLE IF NOT EXISTS telegram_accounts (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  type TEXT NOT NULL,
  session_path TEXT,
  phone TEXT,
  bot_token TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  name TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS channel_mappings (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  source_chat_id BIGINT NOT NULL,
  dest_chat_id BIGINT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  name TEXT,
  source_chat_title TEXT,
  dest_chat_title TEXT,
  created_at TEXT,
  telegram_account_id BIGINT REFERENCES telegram_accounts(id),
  send_delay_ms INTEGER NOT NULL DEFAULT 0,
  sync_edits INTEGER NOT NULL DEFAULT 0,
  edit_strategy TEXT NOT NULL DEFAULT 'replace_text',
  sync_deletes INTEGER NOT NULL DEFAULT 0,
  copy_webhook_url TEXT,
  copy_webhook_secret TEXT,
  copy_webhook_payload_template TEXT,
  copy_webhook_secret_header_name TEXT,
  copy_webhook_secret_header_value TEXT,
  copy_webhook_secret_mode TEXT NOT NULL DEFAULT 'hmac_sha256'
);

CREATE TABLE IF NOT EXISTS mapping_filters (
  id BIGSERIAL PRIMARY KEY,
  mapping_id BIGINT NOT NULL REFERENCES channel_mappings(id),
  include_text TEXT,
  exclude_text TEXT,
  media_types TEXT,
  regex_pattern TEXT,
  or_group_id INTEGER,
  allowed_sender_ids TEXT,
  denied_usernames TEXT,
  min_url_count INTEGER,
  max_url_count INTEGER,
  required_hashtags TEXT
);

CREATE TABLE IF NOT EXISTS dest_message_index (
  user_id BIGINT NOT NULL,
  source_chat_id BIGINT NOT NULL,
  source_msg_id BIGINT NOT NULL,
  dest_chat_id BIGINT NOT NULL,
  dest_msg_id BIGINT NOT NULL,
  updated_at TEXT,
  PRIMARY KEY (user_id, source_chat_id, source_msg_id, dest_chat_id)
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  token_hash TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS admin_invites (
  id BIGSERIAL PRIMARY KEY,
  email TEXT NOT NULL,
  token TEXT NOT NULL UNIQUE,
  created_by BIGINT NOT NULL REFERENCES users(id),
  expires_at TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app_settings (
  key TEXT PRIMARY KEY,
  value TEXT,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS login_sessions (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  phone TEXT NOT NULL,
  tmp_session_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  phone_code_hash TEXT
);

CREATE TABLE IF NOT EXISTS worker_registry (
  worker_id TEXT PRIMARY KEY,
  user_id BIGINT NOT NULL,
  account_id BIGINT NOT NULL,
  session_path TEXT NOT NULL,
  pid INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_heartbeat_at TEXT
);

CREATE TABLE IF NOT EXISTS user_schedules (
  user_id BIGINT PRIMARY KEY REFERENCES users(id),
  mon_start_utc TEXT, mon_end_utc TEXT,
  tue_start_utc TEXT, tue_end_utc TEXT,
  wed_start_utc TEXT, wed_end_utc TEXT,
  thu_start_utc TEXT, thu_end_utc TEXT,
  fri_start_utc TEXT, fri_end_utc TEXT,
  sat_start_utc TEXT, sat_end_utc TEXT,
  sun_start_utc TEXT, sun_end_utc TEXT
);

CREATE TABLE IF NOT EXISTS mapping_schedules (
  mapping_id BIGINT PRIMARY KEY REFERENCES channel_mappings(id),
  mon_start_utc TEXT, mon_end_utc TEXT,
  tue_start_utc TEXT, tue_end_utc TEXT,
  wed_start_utc TEXT, wed_end_utc TEXT,
  thu_start_utc TEXT, thu_end_utc TEXT,
  fri_start_utc TEXT, fri_end_utc TEXT,
  sat_start_utc TEXT, sat_end_utc TEXT,
  sun_start_utc TEXT, sun_end_utc TEXT
);

CREATE TABLE IF NOT EXISTS mapping_transform_rules (
  id BIGSERIAL PRIMARY KEY,
  mapping_id BIGINT NOT NULL REFERENCES channel_mappings(id),
  rule_type TEXT NOT NULL,
  find_text TEXT,
  replace_text TEXT,
  regex_pattern TEXT,
  regex_flags TEXT,
  enabled INTEGER NOT NULL DEFAULT 1,
  priority INTEGER NOT NULL DEFAULT 100,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  replacement_media_asset_id BIGINT,
  apply_to_media_types TEXT
);

CREATE TABLE IF NOT EXISTS media_assets (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  name TEXT NOT NULL,
  file_path TEXT NOT NULL,
  media_kind TEXT NOT NULL DEFAULT 'other',
  mime_type TEXT,
  size_bytes BIGINT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_alert_webhooks (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  url TEXT NOT NULL,
  secret TEXT,
  enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_api_keys (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  name TEXT NOT NULL,
  key_hash TEXT NOT NULL,
  scopes TEXT NOT NULL DEFAULT 'mappings:read',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_used_at TEXT
);

CREATE TABLE IF NOT EXISTS _migrations (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_refresh_tokens_token_hash ON refresh_tokens(token_hash);
CREATE INDEX IF NOT EXISTS ix_users_id_status ON users(id, status);
CREATE INDEX IF NOT EXISTS ix_telegram_accounts_user_id ON telegram_accounts(user_id);
CREATE INDEX IF NOT EXISTS ix_telegram_accounts_user_status ON telegram_accounts(user_id, status);
CREATE INDEX IF NOT EXISTS ix_channel_mappings_user_id ON channel_mappings(user_id);
CREATE INDEX IF NOT EXISTS ix_channel_mappings_user_src_dest ON channel_mappings(user_id, source_chat_id, dest_chat_id);
CREATE INDEX IF NOT EXISTS ix_mapping_filters_mapping_id ON mapping_filters(mapping_id);
CREATE INDEX IF NOT EXISTS ix_dest_message_index_user_id ON dest_message_index(user_id);
CREATE INDEX IF NOT EXISTS ix_mapping_transform_rules_mapping_id ON mapping_transform_rules(mapping_id);
CREATE INDEX IF NOT EXISTS ix_media_assets_user_id ON media_assets(user_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_worker_registry_account_id ON worker_registry(account_id);
CREATE INDEX IF NOT EXISTS ix_user_alert_webhooks_user_id ON user_alert_webhooks(user_id);
CREATE INDEX IF NOT EXISTS ix_user_api_keys_user_id ON user_api_keys(user_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_user_api_keys_key_hash ON user_api_keys(key_hash);
"""

_QMARK_RE = re.compile(r"\?")
_INSERT_TABLE_RE = re.compile(r"^\s*INSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.IGNORECASE)
_ENGINE: AsyncEngine | None = None
TRANSIENT_POSTGRES_SQLSTATES = {"40P01", "40001"}
_TABLES_WITH_ID = {
    "users",
    "telegram_accounts",
    "channel_mappings",
    "mapping_filters",
    "refresh_tokens",
    "admin_invites",
    "login_sessions",
    "mapping_transform_rules",
    "media_assets",
    "user_alert_webhooks",
    "user_api_keys",
}


def using_postgres() -> bool:
    backend = (settings.db_backend or "").strip().lower()
    return backend == "postgres"


def _get_engine() -> AsyncEngine:
    global _ENGINE
    if _ENGINE is None:
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL is required for PostgreSQL mode")
        _ENGINE = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
            poolclass=NullPool,
            future=True,
        )
    return _ENGINE


def _translate_qmark(sql: str, params: Sequence[Any] | None) -> tuple[str, dict[str, Any]]:
    if not params:
        return sql, {}
    idx = 0
    mapped: dict[str, Any] = {}

    def repl(_: re.Match[str]) -> str:
        nonlocal idx
        key = f"p{idx}"
        mapped[key] = params[idx]
        idx += 1
        return f":{key}"

    translated = _QMARK_RE.sub(repl, sql)
    return translated, mapped


def _as_db_exception(err: Exception) -> Exception:
    msg = str(err).lower()
    if isinstance(err, SAIntegrityError):
        return aiosqlite.IntegrityError(str(err))
    if isinstance(err, SAOperationalError) or "deadlock" in msg or "timeout" in msg:
        return aiosqlite.OperationalError(str(err))
    return err


def is_transient_postgres_error(err: Exception) -> bool:
    """True for retryable PostgreSQL concurrency/transaction conflicts."""
    cursor: Exception | None = err
    while cursor is not None:
        sqlstate = (
            getattr(cursor, "sqlstate", None)
            or getattr(cursor, "pgcode", None)
            or getattr(getattr(cursor, "orig", None), "sqlstate", None)
            or getattr(getattr(cursor, "orig", None), "pgcode", None)
        )
        if isinstance(sqlstate, str) and sqlstate in TRANSIENT_POSTGRES_SQLSTATES:
            return True
        text = str(cursor)
        if "40P01" in text or "40001" in text:
            return True
        cursor = getattr(cursor, "__cause__", None)
    return False


async def retry_transient_postgres(
    operation,
    *,
    retries: int = 3,
    base_delay_s: float = 0.05,
    operation_name: str = "postgres_operation",
):
    """Retry wrapper for transient PostgreSQL transaction conflicts."""
    attempt = 0
    while True:
        try:
            return await operation()
        except Exception as err:
            attempt += 1
            if attempt >= retries or not is_transient_postgres_error(err):
                raise
            jitter = random.uniform(0.0, base_delay_s)
            sleep_s = base_delay_s * attempt + jitter
            logger.warning(
                "retry_transient_postgres: retrying op=%s attempt=%d/%d sqlstate=%s sleep_s=%.3f",
                operation_name,
                attempt,
                retries,
                getattr(err, "sqlstate", None) or getattr(getattr(err, "orig", None), "sqlstate", None),
                sleep_s,
            )
            await asyncio.sleep(sleep_s)


class PostgresCompatCursor:
    def __init__(
        self,
        conn: AsyncConnection,
        result: Any,
        rowcount: int | None = None,
        lastrowid: int | None = None,
    ) -> None:
        self._conn = conn
        self._result = result
        self.rowcount = rowcount if rowcount is not None else 0
        self.lastrowid = lastrowid

    async def __aenter__(self) -> "PostgresCompatCursor":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def fetchone(self):
        row = self._result.fetchone()
        return tuple(row) if row is not None else None

    async def fetchall(self):
        rows = self._result.fetchall()
        return [tuple(r) for r in rows]


class PostgresCompatConnection:
    def __init__(self, conn: AsyncConnection):
        self._conn = conn
        self._tx = None

    async def _execute_impl(
        self,
        sql: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> PostgresCompatCursor:
        try:
            bind_params: dict[str, Any]
            if isinstance(params, dict):
                translated_sql, bind_params = sql, params
            else:
                translated_sql, bind_params = _translate_qmark(sql, params)

            sql_to_run = translated_sql
            lastrowid = None
            is_insert = translated_sql.strip().upper().startswith("INSERT")
            if is_insert and "RETURNING" not in translated_sql.upper():
                match = _INSERT_TABLE_RE.match(translated_sql)
                table = match.group(1).lower() if match else ""
                if table in _TABLES_WITH_ID:
                    sql_to_run = f"{translated_sql} RETURNING id"

            result = await self._conn.execute(text(sql_to_run), bind_params)
            lastrowid = None
            if is_insert and sql_to_run != translated_sql:
                row = result.fetchone()
                if row and len(row) > 0:
                    try:
                        lastrowid = int(row[0])
                    except (TypeError, ValueError):
                        lastrowid = None
            return PostgresCompatCursor(
                self._conn,
                result=result,
                rowcount=result.rowcount,
                lastrowid=lastrowid,
            )
        except Exception as err:
            if self._tx is not None:
                try:
                    await self._tx.rollback()
                except Exception:
                    pass
                self._tx = await self._conn.begin()
            raise _as_db_exception(err) from err

    def execute(
        self,
        sql: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ):
        return PostgresExecuteProxy(self, sql, params)

    async def executemany(self, sql: str, seq_of_params: Iterable[Sequence[Any]]):
        cursor = None
        for params in seq_of_params:
            cursor = await self.execute(sql, params)
        return cursor or PostgresCompatCursor(self._conn, result=await self._conn.execute(text("SELECT 1")))

    async def executescript(self, script: str) -> None:
        for stmt in script.split(";"):
            query = stmt.strip()
            if not query:
                continue
            await self.execute(query)

    async def commit(self) -> None:
        if self._tx is not None:
            await self._tx.commit()
            self._tx = await self._conn.begin()

    async def close(self) -> None:
        if self._tx is not None:
            try:
                await self._tx.commit()
            except Exception:
                await self._tx.rollback()
            self._tx = None
        await self._conn.close()


class PostgresExecuteProxy:
    """Supports both `await db.execute(...)` and `async with db.execute(...)`."""

    def __init__(
        self,
        db: PostgresCompatConnection,
        sql: str,
        params: Sequence[Any] | dict[str, Any] | None,
    ) -> None:
        self._db = db
        self._sql = sql
        self._params = params
        self._cursor: PostgresCompatCursor | None = None

    def __await__(self):
        return self._db._execute_impl(self._sql, self._params).__await__()

    async def __aenter__(self) -> PostgresCompatCursor:
        self._cursor = await self._db._execute_impl(self._sql, self._params)
        return self._cursor

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self._cursor = None
        return None


async def get_postgres_connection() -> Any:
    engine = _get_engine()
    conn = await engine.connect()
    compat = PostgresCompatConnection(conn)
    compat._tx = await conn.begin()
    return compat


async def init_postgres() -> None:
    engine = _get_engine()
    async with engine.begin() as conn:
        for stmt in POSTGRES_SCHEMA_SQL.split(";"):
            query = stmt.strip()
            if not query:
                continue
            await conn.execute(text(query))
        await conn.execute(
            text("INSERT INTO _migrations (id, name, applied_at) VALUES (0, :name, :applied_at) ON CONFLICT DO NOTHING"),
            {"name": "v1_base", "applied_at": datetime.now(timezone.utc).isoformat()},
        )
