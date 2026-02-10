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


@cli.command()
def run_worker(user_id: int, session_path: str) -> None:
    """Run a Telegram sync worker for a user session."""
    from app.worker import run_worker_sync

    run_worker_sync(user_id=user_id, session_path=session_path)

