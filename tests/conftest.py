"""Root conftest - set TESTING before any app imports to skip slow startup in tests."""
import os

os.environ["TESTING"] = "1"  # Skip Mongo indexes, 3s worker restore delay in API tests
os.environ["DB_BACKEND"] = "postgres"
# IMPORTANT: keep tests isolated from dev runtime DB.
# Tests always use TEST_DATABASE_URL (or a safe default test DB).
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/telegram_copier_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import asyncio

import asyncpg
import pytest


@pytest.fixture(scope="session", autouse=True)
def clear_stale_postgres_test_backends() -> None:
    """Best-effort cleanup of stale local test sessions before pytest starts.

    Interrupted Windows runs can leave idle transactions that hold table locks and
    make subsequent local test runs appear hung.
    """

    async def _cleanup() -> None:
        dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(dsn)
        try:
            await conn.execute(
                """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = current_database()
                  AND pid <> pg_backend_pid()
                """
            )
        finally:
            await conn.close()

    asyncio.run(_cleanup())

