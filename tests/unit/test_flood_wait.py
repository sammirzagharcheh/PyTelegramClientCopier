"""Unit tests for FloodWait retry helper."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from telethon.errors import FloodWaitError

from app.telegram.flood_wait import call_with_flood_retry, flood_skip_detail


@pytest.mark.asyncio
async def test_flood_wait_retries_then_succeeds():
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise FloodWaitError(request=None, capture=5)
        return "ok"

    with patch("app.telegram.flood_wait.asyncio.sleep", new_callable=AsyncMock) as sleep:
        result = await call_with_flood_retry(flaky, max_seconds=120, retries=1)

    assert result.value == "ok"
    assert result.exhausted is False
    assert result.waited_seconds == 5
    sleep.assert_awaited_once_with(5)


@pytest.mark.asyncio
async def test_flood_wait_over_cap_gives_up_without_sleep():
    async def always_flood():
        raise FloodWaitError(request=None, capture=500)

    with patch("app.telegram.flood_wait.asyncio.sleep", new_callable=AsyncMock) as sleep:
        result = await call_with_flood_retry(always_flood, max_seconds=120, retries=1)

    assert result.exhausted is True
    assert result.value is None
    assert isinstance(result.flood_error, FloodWaitError)
    sleep.assert_not_awaited()
    assert flood_skip_detail(result.flood_error) == "seconds=500"


@pytest.mark.asyncio
async def test_flood_wait_retries_exhausted():
    async def always_flood():
        raise FloodWaitError(request=None, capture=2)

    with patch("app.telegram.flood_wait.asyncio.sleep", new_callable=AsyncMock) as sleep:
        result = await call_with_flood_retry(always_flood, max_seconds=120, retries=1)

    assert result.exhausted is True
    assert sleep.await_count == 1
