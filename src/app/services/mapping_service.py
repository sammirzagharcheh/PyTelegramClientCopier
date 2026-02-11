from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import aiosqlite


@dataclass(slots=True)
class MappingFilter:
    include_text: str | None
    exclude_text: str | None
    media_types: str | None
    regex_pattern: str | None


@dataclass(slots=True)
class ChannelMapping:
    id: int
    user_id: int
    source_chat_id: int
    dest_chat_id: int
    enabled: bool
    filters: list[MappingFilter]


async def list_enabled_mappings(
    db: aiosqlite.Connection,
    user_id: int,
    telegram_account_id: int | None = None,
) -> Iterable[ChannelMapping]:
    """List enabled mappings for a user. If telegram_account_id is given, include only mappings
    that have no account or that account (telegram_account_id IS NULL OR telegram_account_id = ?).
    """
    mappings: list[ChannelMapping] = []
    if telegram_account_id is not None:
        q = (
            "SELECT id, user_id, source_chat_id, dest_chat_id, enabled "
            "FROM channel_mappings WHERE user_id = ? AND enabled = 1 "
            "AND (telegram_account_id IS NULL OR telegram_account_id = ?)"
        )
        params = (user_id, telegram_account_id)
    else:
        q = (
            "SELECT id, user_id, source_chat_id, dest_chat_id, enabled "
            "FROM channel_mappings WHERE user_id = ? AND enabled = 1"
        )
        params = (user_id,)
    async with db.execute(q, params) as cursor:
        rows = await cursor.fetchall()
    for mapping_id, u_id, source_id, dest_id, enabled in rows:
        filters = await _list_filters(db, user_id, mapping_id)
        mappings.append(
            ChannelMapping(
                id=mapping_id,
                user_id=u_id,
                source_chat_id=source_id,
                dest_chat_id=dest_id,
                enabled=bool(enabled),
                filters=filters,
            )
        )
    return mappings


async def _list_filters(db: aiosqlite.Connection, user_id: int, mapping_id: int) -> list[MappingFilter]:
    async with db.execute(
        "SELECT mf.include_text, mf.exclude_text, mf.media_types, mf.regex_pattern "
        "FROM mapping_filters mf "
        "JOIN channel_mappings cm ON cm.id = mf.mapping_id "
        "WHERE mf.mapping_id = ? AND cm.user_id = ?",
        (mapping_id, user_id),
    ) as cursor:
        rows = await cursor.fetchall()
    return [
        MappingFilter(
            include_text=row[0],
            exclude_text=row[1],
            media_types=row[2],
            regex_pattern=row[3],
        )
        for row in rows
    ]

