from __future__ import annotations

import asyncio
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import typer

from app.config import settings
from app.db.gateway import get_db_connection, init_db as init_database


cli = typer.Typer(help="Telegram Client Copier CLI")


@cli.command()
def init_db() -> None:
    """Initialize the configured SQL schema."""
    asyncio.run(init_database())
    typer.echo(f"{settings.db_backend.upper()} schema initialized.")


@cli.command()
def show_config() -> None:
    """Print loaded config (non-sensitive)."""
    typer.echo(f"DB backend: {settings.db_backend}")
    typer.echo(f"Database URL set: {bool(settings.database_url)}")
    typer.echo(f"MongoDB: {settings.mongo_uri}/{settings.mongo_db}")
    typer.echo(f"API_ID set: {settings.api_id is not None}")
    typer.echo(f"API_HASH set: {settings.api_hash is not None}")


@cli.command("test-mongo")
def test_mongo(
    write: bool = typer.Option(False, "--write", "-w", help="Also test write/read/delete"),
) -> None:
    """Test MongoDB connection (uses app_settings override or .env)."""
    from app.db.mongo import _resolve_mongo_db, _resolve_mongo_uri
    from app.services.app_settings import mask_mongo_uri

    uri = _resolve_mongo_uri()
    db_name = _resolve_mongo_db()
    typer.echo(f"URI: {mask_mongo_uri(uri)}")
    typer.echo(f"DB:  {db_name}")

    async def _run():
        from app.db.mongo import get_mongo_db

        mongo_db = get_mongo_db()
        await mongo_db.command("ping")
        typer.echo(typer.style("OK - Ping", fg=typer.colors.GREEN))

        if write:
            col = mongo_db["_connection_test"]
            doc = {"_test": True, "source": "cli", "value": 123}
            r = await col.insert_one(doc)
            assert r.inserted_id
            found = await col.find_one({"_id": r.inserted_id})
            assert found and found["value"] == 123
            await col.delete_one({"_id": r.inserted_id})
            typer.echo(typer.style("OK - Write/read/delete", fg=typer.colors.GREEN))

    try:
        asyncio.run(_run())
        typer.echo("MongoDB connection OK.")
    except Exception as e:
        typer.echo(typer.style(f"FAIL - {e}", fg=typer.colors.RED), err=True)
        raise typer.Exit(1)


@cli.command()
def run_worker(
    user_id: int,
    session_path: str,
    account_id: int | None = typer.Option(None, help="Telegram account ID (filters mappings)"),
) -> None:
    """Run a Telegram sync worker for a user session."""
    from app.worker import run_worker_sync

    run_worker_sync(
        user_id=user_id,
        session_path=session_path,
        telegram_account_id=account_id,
    )


@cli.command("show-mappings")
def show_mappings(
    user_id: int = typer.Argument(..., help="User ID"),
    account_id: int | None = typer.Option(None, "--account-id", "-a", help="Telegram account ID (filters mappings)"),
) -> None:
    """Show mappings that a worker would load for debugging."""
    from app.services.mapping_service import list_enabled_mappings

    async def _run():
        await init_database()
        db = await get_db_connection()
        mappings = list(
            await list_enabled_mappings(db, user_id, telegram_account_id=account_id)
        )
        await db.close()
        return mappings

    mappings = asyncio.run(_run())
    typer.echo(f"Mappings for user_id={user_id} account_id={account_id}: {len(mappings)}")
    for m in mappings:
        typer.echo(f"  id={m.id} source={m.source_chat_id} dest={m.dest_chat_id} filters={len(m.filters)}")
    if not mappings:
        typer.echo("  (none - worker would not forward messages)")


@cli.command()
def create_admin(email: str, password: str, name: str = "") -> None:
    """Create an admin user (for bootstrap)."""
    from app.auth.password import hash_password

    async def _create():
        await init_database()
        db = await get_db_connection()
        try:
            pw_hash = hash_password(password)
            await db.execute(
                """INSERT INTO users (email, password_hash, name, role, status)
                   VALUES (?, ?, ?, 'admin', 'active')""",
                (email.lower(), pw_hash, name or email.split("@")[0]),
            )
            await db.commit()
            typer.echo(f"Admin created: {email}")
        except Exception as e:
            if "UNIQUE" in str(e) or "unique" in str(e).lower():
                typer.echo(f"Error: Email {email} already exists", err=True)
            else:
                raise
        finally:
            await db.close()

    asyncio.run(_create())


@cli.command("set-password")
def set_password(
    email: str = typer.Argument(..., help="User email (matched case-insensitively)"),
    password: str = typer.Argument(..., help="New password"),
) -> None:
    """Overwrite password for an existing user (recovery after DB migration or lockout)."""
    from app.auth.password import hash_password

    async def _set() -> None:
        await init_database()
        db = await get_db_connection()
        try:
            async with db.execute(
                "SELECT id FROM users WHERE lower(email) = ?",
                (email.lower(),),
            ) as cur:
                row = await cur.fetchone()
            if not row:
                typer.echo(f"No user with email matching {email!r}.", err=True)
                raise typer.Exit(1)
            pw_hash = hash_password(password)
            now = datetime.now(timezone.utc)
            await db.execute(
                "UPDATE users SET password_hash = ?, updated_at = ? WHERE lower(email) = ?",
                (pw_hash, now, email.lower()),
            )
            await db.commit()
            typer.echo(f"Password updated for user id={row[0]}.")
        finally:
            await db.close()

    asyncio.run(_set())


@cli.command("inspect-auth-users")
def inspect_auth_users() -> None:
    """Print safe auth fields per user (debug login: status, hash shape, bcrypt prefix)."""
    from app.auth.password import _normalize_bcrypt_hash

    async def _run() -> None:
        await init_database()
        db = await get_db_connection()
        try:
            async with db.execute(
                "SELECT id, email, status, password_hash FROM users ORDER BY id"
            ) as cur:
                rows = await cur.fetchall()
            if not rows:
                typer.echo("No rows in users table.")
                return
            for row in rows:
                uid, email, user_status, ph = row
                norm = _normalize_bcrypt_hash(ph)
                ph_type = type(ph).__name__
                if ph is None:
                    ph_len = 0
                elif isinstance(ph, memoryview):
                    ph_len = len(ph.tobytes())
                else:
                    ph_len = len(ph)
                preview = ""
                if ph is not None:
                    s = (
                        ph.decode("utf-8", errors="replace")
                        if isinstance(ph, (bytes, memoryview))
                        else str(ph)
                    )
                    preview = (s[:18] + "…") if len(s) > 18 else s
                typer.echo(
                    f"id={uid} email={email!r} status={user_status!r} "
                    f"hash_type={ph_type} hash_len={ph_len} bcrypt_ok={bool(norm)} "
                    f"prefix={preview!r}"
                )
        finally:
            await db.close()

    asyncio.run(_run())


@cli.command("purge-message-index")
def purge_message_index(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Report how many orphan rows would be deleted without deleting",
    ),
) -> None:
    """Remove dest_message_index rows that no longer match any channel mapping."""
    from app.db.message_index_cleanup import purge_orphan_dest_message_index

    async def _run() -> int:
        await init_database()
        db = await get_db_connection()
        try:
            return await purge_orphan_dest_message_index(db, dry_run=dry_run)
        finally:
            await db.close()

    n = asyncio.run(_run())
    if dry_run:
        typer.echo(f"Dry run: {n} orphan dest_message_index row(s) would be removed.")
    else:
        typer.echo(f"Removed {n} orphan dest_message_index row(s).")


@cli.command("import-sqlite")
def import_sqlite(
    sqlite_path: str = typer.Argument("data/app.db", help="Path to source SQLite DB file"),
    replace_existing: bool = typer.Option(
        True,
        "--replace-existing/--keep-existing",
        help="Clear PostgreSQL tables before import.",
    ),
) -> None:
    """Import legacy SQLite data into PostgreSQL runtime DB."""

    table_order = [
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
    sequence_tables = [
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

    def _parse_sqlite_dt(value):
        if value is None or not isinstance(value, str):
            return value
        s = value.strip()
        if not s:
            return None
        s = s.replace("Z", "+00:00")
        if " " in s and "T" not in s:
            s = s.replace(" ", "T", 1)
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            return value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    async def _run() -> None:
        await init_database()
        db = await get_db_connection()
        src_path = Path(sqlite_path)
        if not src_path.is_absolute():
            src_path = (Path(__file__).resolve().parents[3] / src_path).resolve()
        if not src_path.exists():
            await db.close()
            raise typer.BadParameter(f"SQLite file not found: {src_path}")

        src = sqlite3.connect(str(src_path))
        src.row_factory = sqlite3.Row
        imported_counts: dict[str, int] = {}
        try:
            sqlite_tables = {
                r["name"]
                for r in src.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                ).fetchall()
            }
            if not sqlite_tables:
                typer.echo("No tables found in SQLite source; nothing to import.")
                return

            if replace_existing:
                for table in reversed(table_order):
                    if table in sqlite_tables:
                        await db.execute(f'DELETE FROM "{table}"')
                await db.commit()

            for table in table_order:
                if table not in sqlite_tables:
                    continue

                # Source columns from SQLite
                pragma_rows = src.execute(f'PRAGMA table_info("{table}")').fetchall()
                sqlite_cols = [r["name"] for r in pragma_rows]
                if not sqlite_cols:
                    continue

                # Target columns from PostgreSQL
                async with db.execute(
                    """
                    SELECT column_name, data_type, udt_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = ?
                    ORDER BY ordinal_position
                    """,
                    (table,),
                ) as cur:
                    pg_col_rows = await cur.fetchall()
                    pg_cols = [r[0] for r in pg_col_rows]
                    pg_col_types = {r[0]: (r[1], r[2]) for r in pg_col_rows}
                if not pg_cols:
                    continue

                cols = [c for c in sqlite_cols if c in pg_cols]
                if not cols:
                    continue

                col_sql = ", ".join(f'"{c}"' for c in cols)
                placeholder_sql = ", ".join("?" for _ in cols)
                rows = src.execute(f'SELECT {col_sql} FROM "{table}"').fetchall()
                inserted = 0
                for row in rows:
                    params = []
                    for c in cols:
                        v = row[c]
                        data_type, udt_name = pg_col_types.get(c, ("", ""))
                        if str(data_type).startswith("timestamp") or udt_name in {
                            "timestamp",
                            "timestamptz",
                        }:
                            v = _parse_sqlite_dt(v)
                        params.append(v)
                    await db.execute(
                        f'INSERT INTO "{table}" ({col_sql}) VALUES ({placeholder_sql})',
                        tuple(params),
                    )
                    inserted += 1
                imported_counts[table] = inserted
                await db.commit()

            # Reset serial sequences to imported max(id)
            for table in sequence_tables:
                if table not in imported_counts:
                    continue
                seq_name = f"{table}_id_seq"
                await db.execute(
                    f"""
                    SELECT setval(
                        '{seq_name}',
                        COALESCE((SELECT MAX(id) FROM "{table}"), 1),
                        (SELECT COUNT(*) > 0 FROM "{table}")
                    )
                    """
                )
            await db.commit()
        finally:
            src.close()
            await db.close()

        total_rows = sum(imported_counts.values())
        typer.echo(f"Imported {total_rows} rows from {src_path}")
        for table, cnt in imported_counts.items():
            typer.echo(f"  {table}: {cnt}")

    asyncio.run(_run())

