from __future__ import annotations

import asyncio

import typer

from app.config import settings
from app.db.sqlite import init_sqlite


cli = typer.Typer(help="Telegram Client Copier CLI")


@cli.command()
def init_db() -> None:
    """Initialize SQLite schema."""
    asyncio.run(init_sqlite())
    typer.echo("SQLite schema initialized.")


@cli.command()
def show_config() -> None:
    """Print loaded config (non-sensitive)."""
    typer.echo(f"SQLite: {settings.sqlite_path}")
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
    from app.db.sqlite import get_sqlite, init_sqlite
    from app.services.mapping_service import list_enabled_mappings

    async def _run():
        await init_sqlite()
        db = await get_sqlite()
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
    from app.db.sqlite import get_sqlite

    asyncio.run(init_sqlite())

    async def _create():
        db = await get_sqlite()
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

