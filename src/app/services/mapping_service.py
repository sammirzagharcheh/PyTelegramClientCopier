from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import aiosqlite


@dataclass(slots=True)
class MappingFilter:
    include_text: str | None
    exclude_text: str | None
    media_types: str | None
    regex_pattern: str | None


@dataclass(slots=True)
class MappingTransform:
    id: int
    rule_type: str
    find_text: str | None = None
    replace_text: str | None = None
    regex_pattern: str | None = None
    regex_flags: str | None = None
    replacement_media_asset_id: int | None = None
    apply_to_media_types: str | None = None
    replacement_media_asset_path: str | None = None
    replacement_media_kind: str | None = None
    enabled: bool = True
    priority: int = 100


WEEKDAY_COLS = [
    "mon_start_utc", "mon_end_utc",
    "tue_start_utc", "tue_end_utc",
    "wed_start_utc", "wed_end_utc",
    "thu_start_utc", "thu_end_utc",
    "fri_start_utc", "fri_end_utc",
    "sat_start_utc", "sat_end_utc",
    "sun_start_utc", "sun_end_utc",
]


@dataclass(slots=True)
class Schedule:
    """Time-of-day schedule per weekday. All times in UTC HH:MM. None = unrestricted for that slot."""

    mon_start_utc: str | None
    mon_end_utc: str | None
    tue_start_utc: str | None
    tue_end_utc: str | None
    wed_start_utc: str | None
    wed_end_utc: str | None
    thu_start_utc: str | None
    thu_end_utc: str | None
    fri_start_utc: str | None
    fri_end_utc: str | None
    sat_start_utc: str | None
    sat_end_utc: str | None
    sun_start_utc: str | None
    sun_end_utc: str | None

    def get_for_weekday(self, weekday: int) -> tuple[str | None, str | None]:
        """weekday: 0=Monday, 6=Sunday. Returns (start_utc, end_utc)."""
        idx = weekday * 2
        start = (
            self.mon_start_utc, self.tue_start_utc, self.wed_start_utc, self.thu_start_utc,
            self.fri_start_utc, self.sat_start_utc, self.sun_start_utc,
        )[weekday]
        end = (
            self.mon_end_utc, self.tue_end_utc, self.wed_end_utc, self.thu_end_utc,
            self.fri_end_utc, self.sat_end_utc, self.sun_end_utc,
        )[weekday]
        return (start, end)

    def is_empty(self) -> bool:
        """True if no day has any restriction."""
        for i in range(7):
            s, e = self.get_for_weekday(i)
            if s is not None or e is not None:
                return False
        return True


@dataclass(slots=True)
class ChannelMapping:
    id: int
    user_id: int
    source_chat_id: int
    dest_chat_id: int
    enabled: bool
    filters: list[MappingFilter]
    source_chat_title: str | None
    dest_chat_title: str | None
    transforms: list[MappingTransform] = field(default_factory=list)
    schedule: Schedule | None = None


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
            "SELECT id, user_id, source_chat_id, dest_chat_id, enabled, source_chat_title, dest_chat_title "
            "FROM channel_mappings WHERE user_id = ? AND enabled = 1 "
            "AND (telegram_account_id IS NULL OR telegram_account_id = ?)"
        )
        params = (user_id, telegram_account_id)
    else:
        q = (
            "SELECT id, user_id, source_chat_id, dest_chat_id, enabled, source_chat_title, dest_chat_title "
            "FROM channel_mappings WHERE user_id = ? AND enabled = 1"
        )
        params = (user_id,)
    async with db.execute(q, params) as cursor:
        rows = await cursor.fetchall()

    if not rows:
        return mappings

    user_schedule = await _load_user_schedule(db, user_id)
    mapping_ids = [row[0] for row in rows]

    # Batch load filters, transforms, and schedules to avoid N+1 queries
    filters_by_mapping = await _list_filters_batch(db, user_id, mapping_ids)
    transforms_by_mapping = await _list_transforms_batch(db, user_id, mapping_ids)
    schedules_by_mapping = await _load_mapping_schedules_batch(db, mapping_ids)

    for mapping_id, u_id, source_id, dest_id, enabled, src_title, dest_title in rows:
        schedule = schedules_by_mapping.get(mapping_id) or user_schedule
        mappings.append(
            ChannelMapping(
                id=mapping_id,
                user_id=u_id,
                source_chat_id=source_id,
                dest_chat_id=dest_id,
                enabled=bool(enabled),
                filters=filters_by_mapping.get(mapping_id, []),
                source_chat_title=src_title or None,
                dest_chat_title=dest_title or None,
                transforms=transforms_by_mapping.get(mapping_id, []),
                schedule=schedule,
            )
        )
    return mappings


def _row_to_schedule(row: tuple) -> Schedule | None:
    """Convert a 14-tuple (mon_start, mon_end, ..., sun_start, sun_end) to Schedule."""
    if not row or all(x is None for x in row):
        return None
    return Schedule(
        mon_start_utc=row[0], mon_end_utc=row[1],
        tue_start_utc=row[2], tue_end_utc=row[3],
        wed_start_utc=row[4], wed_end_utc=row[5],
        thu_start_utc=row[6], thu_end_utc=row[7],
        fri_start_utc=row[8], fri_end_utc=row[9],
        sat_start_utc=row[10], sat_end_utc=row[11],
        sun_start_utc=row[12], sun_end_utc=row[13],
    )


async def _load_user_schedule(db: aiosqlite.Connection, user_id: int) -> Schedule | None:
    cols = ", ".join(WEEKDAY_COLS)
    async with db.execute(
        f"SELECT {cols} FROM user_schedules WHERE user_id = ?",
        (user_id,),
    ) as cursor:
        row = await cursor.fetchone()
    if not row:
        return None
    return _row_to_schedule(row)


async def _load_mapping_schedule(
    db: aiosqlite.Connection,
    mapping_id: int,
    user_id: int,
    user_schedule: Schedule | None,
) -> Schedule | None:
    """Use mapping override if exists, else user schedule."""
    cols = ", ".join(WEEKDAY_COLS)
    async with db.execute(
        f"SELECT {cols} FROM mapping_schedules WHERE mapping_id = ?",
        (mapping_id,),
    ) as cursor:
        row = await cursor.fetchone()
    if row and any(x is not None for x in row):
        return _row_to_schedule(row)
    return user_schedule


async def _list_filters_batch(
    db: aiosqlite.Connection, user_id: int, mapping_ids: list[int]
) -> dict[int, list[MappingFilter]]:
    """Load filters for multiple mappings in a single query."""
    if not mapping_ids:
        return {}
    placeholders = ",".join("?" * len(mapping_ids))
    async with db.execute(
        f"SELECT mf.mapping_id, mf.include_text, mf.exclude_text, mf.media_types, mf.regex_pattern "
        f"FROM mapping_filters mf "
        f"JOIN channel_mappings cm ON cm.id = mf.mapping_id "
        f"WHERE mf.mapping_id IN ({placeholders}) AND cm.user_id = ?",
        (*mapping_ids, user_id),
    ) as cursor:
        rows = await cursor.fetchall()
    result: dict[int, list[MappingFilter]] = {mid: [] for mid in mapping_ids}
    for row in rows:
        result[row[0]].append(
            MappingFilter(
                include_text=row[1],
                exclude_text=row[2],
                media_types=row[3],
                regex_pattern=row[4],
            )
        )
    return result


async def _list_transforms_batch(
    db: aiosqlite.Connection, user_id: int, mapping_ids: list[int]
) -> dict[int, list[MappingTransform]]:
    """Load transforms for multiple mappings in a single query."""
    if not mapping_ids:
        return {}
    placeholders = ",".join("?" * len(mapping_ids))
    async with db.execute(
        f"SELECT tr.mapping_id, tr.id, tr.rule_type, tr.find_text, tr.replace_text, tr.regex_pattern, "
        f"tr.regex_flags, tr.replacement_media_asset_id, tr.apply_to_media_types, "
        f"ma.file_path, ma.media_kind, tr.enabled, tr.priority "
        f"FROM mapping_transform_rules tr "
        f"JOIN channel_mappings cm ON cm.id = tr.mapping_id "
        f"LEFT JOIN media_assets ma ON ma.id = tr.replacement_media_asset_id "
        f"WHERE tr.mapping_id IN ({placeholders}) AND cm.user_id = ? "
        f"ORDER BY tr.priority ASC, tr.id ASC",
        (*mapping_ids, user_id),
    ) as cursor:
        rows = await cursor.fetchall()
    result: dict[int, list[MappingTransform]] = {mid: [] for mid in mapping_ids}
    for row in rows:
        result[row[0]].append(
            MappingTransform(
                id=row[1],
                rule_type=row[2],
                find_text=row[3],
                replace_text=row[4],
                regex_pattern=row[5],
                regex_flags=row[6],
                replacement_media_asset_id=row[7],
                apply_to_media_types=row[8],
                replacement_media_asset_path=row[9],
                replacement_media_kind=row[10],
                enabled=bool(row[11]),
                priority=row[12] if row[12] is not None else 100,
            )
        )
    return result


async def _load_mapping_schedules_batch(
    db: aiosqlite.Connection, mapping_ids: list[int]
) -> dict[int, Schedule | None]:
    """Load schedules for multiple mappings in a single query."""
    if not mapping_ids:
        return {}
    cols = ", ".join(WEEKDAY_COLS)
    placeholders = ",".join("?" * len(mapping_ids))
    async with db.execute(
        f"SELECT mapping_id, {cols} FROM mapping_schedules WHERE mapping_id IN ({placeholders})",
        tuple(mapping_ids),
    ) as cursor:
        rows = await cursor.fetchall()
    result: dict[int, Schedule | None] = {}
    for row in rows:
        mid = row[0]
        schedule_row = row[1:]
        if any(x is not None for x in schedule_row):
            result[mid] = _row_to_schedule(schedule_row)
    return result


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


async def _list_transforms(db: aiosqlite.Connection, user_id: int, mapping_id: int) -> list[MappingTransform]:
    async with db.execute(
        "SELECT tr.id, tr.rule_type, tr.find_text, tr.replace_text, tr.regex_pattern, "
        "tr.regex_flags, tr.replacement_media_asset_id, tr.apply_to_media_types, "
        "ma.file_path, ma.media_kind, tr.enabled, tr.priority "
        "FROM mapping_transform_rules tr "
        "JOIN channel_mappings cm ON cm.id = tr.mapping_id "
        "LEFT JOIN media_assets ma ON ma.id = tr.replacement_media_asset_id "
        "WHERE tr.mapping_id = ? AND cm.user_id = ? "
        "ORDER BY tr.priority ASC, tr.id ASC",
        (mapping_id, user_id),
    ) as cursor:
        rows = await cursor.fetchall()
    return [
        MappingTransform(
            id=row[0],
            rule_type=row[1],
            find_text=row[2],
            replace_text=row[3],
            regex_pattern=row[4],
            regex_flags=row[5],
            replacement_media_asset_id=row[6],
            apply_to_media_types=row[7],
            replacement_media_asset_path=row[8],
            replacement_media_kind=row[9],
            enabled=bool(row[10]),
            priority=row[11] if row[11] is not None else 100,
        )
        for row in rows
    ]

