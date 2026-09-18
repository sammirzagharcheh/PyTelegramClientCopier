"""FloodWait sleep + retry for worker send paths."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from telethon.errors import FloodWaitError

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class FloodWaitResult:
    """Outcome of a send attempt that may have waited for FloodWait."""

    value: Any = None
    flood_error: FloodWaitError | None = None
    exhausted: bool = False
    waited_seconds: int = 0


async def call_with_flood_retry(
    fn: Callable[[], Awaitable[Any]],
    *,
    max_seconds: int = 120,
    retries: int = 1,
    mapping_id: int | None = None,
    dest_id: int | None = None,
) -> FloodWaitResult:
    """Call ``fn``; on FloodWait within cap, sleep and retry up to ``retries`` times.

    If Telegram asks for more than ``max_seconds``, or retries are exhausted,
    return ``exhausted=True`` without sleeping further. Does not catch other errors.
    """
    attempts_left = max(0, int(retries))
    waited_total = 0
    while True:
        try:
            value = await fn()
            return FloodWaitResult(value=value, waited_seconds=waited_total)
        except FloodWaitError as fw:
            seconds = int(getattr(fw, "seconds", 0) or 0)
            logger.warning(
                "FloodWait mapping_id=%s seconds=%s dest=%s attempts_left=%s",
                mapping_id,
                seconds,
                dest_id,
                attempts_left,
            )
            if attempts_left <= 0 or seconds > max_seconds:
                return FloodWaitResult(
                    flood_error=fw,
                    exhausted=True,
                    waited_seconds=waited_total,
                )
            await asyncio.sleep(seconds)
            waited_total += seconds
            attempts_left -= 1
            logger.info(
                "FloodWait slept %ss; retrying mapping_id=%s dest=%s",
                seconds,
                mapping_id,
                dest_id,
            )


def flood_skip_detail(fw: FloodWaitError | None) -> str:
    seconds = int(getattr(fw, "seconds", 0) or 0) if fw is not None else 0
    return f"seconds={seconds}"
