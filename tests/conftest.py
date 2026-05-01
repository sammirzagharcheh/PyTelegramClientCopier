"""Root conftest - set TESTING before any app imports to skip slow startup in tests."""
import os

os.environ["TESTING"] = "1"  # Skip Mongo indexes, 3s worker restore delay in API tests
os.environ["DB_BACKEND"] = "postgres"
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres")

import asyncio

import pytest


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

