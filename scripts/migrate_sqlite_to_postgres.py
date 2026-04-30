from __future__ import annotations

import argparse
import asyncio
import sqlite3
from pathlib import Path

import asyncpg

TABLES_IN_COPY_ORDER = [
    "users",
    "telegram_accounts",
    "channel_mappings",
    "mapping_filters",
    "dest_message_index",
    "refresh_tokens",
    "admin_invites",
    "app_settings",
    "login_sessions",
    "worker_registry",
    "user_schedules",
    "mapping_schedules",
    "mapping_transform_rules",
    "media_assets",
    "user_alert_webhooks",
    "user_api_keys",
    "_migrations",
]

TABLES_WITH_ID_SEQUENCE = [
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
]


def _read_sqlite_table(sqlite_conn: sqlite3.Connection, table: str) -> tuple[list[str], list[tuple]]:
    cols = [r[1] for r in sqlite_conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if not cols:
        return [], []
    rows = sqlite_conn.execute(f'SELECT {", ".join(cols)} FROM "{table}"').fetchall()
    return cols, rows


async def _set_sequences(conn: asyncpg.Connection) -> None:
    for table in TABLES_WITH_ID_SEQUENCE:
        seq = await conn.fetchval("SELECT pg_get_serial_sequence($1, 'id')", table)
        if not seq:
            continue
        max_id = await conn.fetchval(f'SELECT COALESCE(MAX(id), 0) FROM "{table}"')
        if max_id and int(max_id) > 0:
            await conn.execute("SELECT setval($1::regclass, $2::bigint, true)", seq, int(max_id))
        else:
            await conn.execute("SELECT setval($1::regclass, 1, false)", seq)


async def migrate(sqlite_path: Path, postgres_dsn: str) -> None:
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite DB not found: {sqlite_path}")

    sqlite_conn = sqlite3.connect(str(sqlite_path))
    sqlite_conn.row_factory = sqlite3.Row
    try:
        pg = await asyncpg.connect(postgres_dsn)
        try:
            # Start clean so local migration is deterministic/idempotent.
            await pg.execute(
                "TRUNCATE TABLE "
                + ", ".join(f'"{t}"' for t in TABLES_IN_COPY_ORDER)
                + " RESTART IDENTITY CASCADE"
            )

            copied_counts: dict[str, int] = {}
            for table in TABLES_IN_COPY_ORDER:
                cols, rows = _read_sqlite_table(sqlite_conn, table)
                if not cols:
                    copied_counts[table] = 0
                    continue
                if rows:
                    await pg.copy_records_to_table(
                        table_name=table,
                        records=[tuple(r) for r in rows],
                        columns=cols,
                    )
                copied_counts[table] = len(rows)

            await _set_sequences(pg)
        finally:
            await pg.close()
    finally:
        sqlite_conn.close()

    print("SQLite -> PostgreSQL migration complete.")
    for table in TABLES_IN_COPY_ORDER:
        print(f"{table}: {copied_counts.get(table, 0)} rows")


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate local SQLite data into PostgreSQL.")
    parser.add_argument(
        "--sqlite-path",
        default="data/app.db",
        help="Path to source SQLite DB (default: data/app.db)",
    )
    parser.add_argument(
        "--postgres-dsn",
        required=True,
        help="PostgreSQL DSN, e.g. postgresql://user:pass@localhost:5432/dbname",
    )
    args = parser.parse_args()

    asyncio.run(migrate(Path(args.sqlite_path), args.postgres_dsn))


if __name__ == "__main__":
    main()
