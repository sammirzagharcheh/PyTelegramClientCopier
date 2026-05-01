from __future__ import annotations

from app.db.postgres import PostgresCompatConnection, get_postgres_connection, init_postgres


DbConnection = PostgresCompatConnection


async def init_db() -> None:
    await init_postgres()


async def get_db_connection() -> DbConnection:
    return await get_postgres_connection()
