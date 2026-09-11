"""Root conftest - set TESTING before any app imports to skip slow startup in tests."""
import os

os.environ["TESTING"] = "1"  # Skip Mongo indexes, 3s worker restore delay in API tests

import asyncio

import pytest


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

