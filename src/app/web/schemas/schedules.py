"""Schedule Pydantic schemas. All times in UTC HH:MM."""

from __future__ import annotations

import re

from pydantic import BaseModel, field_validator

_UTC_TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
_SCHEDULE_TIME_FIELDS = (
    "mon_start_utc",
    "mon_end_utc",
    "tue_start_utc",
    "tue_end_utc",
    "wed_start_utc",
    "wed_end_utc",
    "thu_start_utc",
    "thu_end_utc",
    "fri_start_utc",
    "fri_end_utc",
    "sat_start_utc",
    "sat_end_utc",
    "sun_start_utc",
    "sun_end_utc",
)


class ScheduleSlot(BaseModel):
    """Start/end for one weekday."""

    start_utc: str | None = None  # HH:MM
    end_utc: str | None = None  # HH:MM

    @field_validator("start_utc", "end_utc")
    @classmethod
    def _validate_slot_time(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not _UTC_TIME_RE.fullmatch(value):
            raise ValueError("Schedule times must use UTC HH:MM (24-hour) format")
        return value


class ScheduleUpdate(BaseModel):
    """14 optional UTC times for Mon-Sun."""

    mon_start_utc: str | None = None
    mon_end_utc: str | None = None
    tue_start_utc: str | None = None
    tue_end_utc: str | None = None
    wed_start_utc: str | None = None
    wed_end_utc: str | None = None
    thu_start_utc: str | None = None
    thu_end_utc: str | None = None
    fri_start_utc: str | None = None
    fri_end_utc: str | None = None
    sat_start_utc: str | None = None
    sat_end_utc: str | None = None
    sun_start_utc: str | None = None
    sun_end_utc: str | None = None

    @field_validator(*_SCHEDULE_TIME_FIELDS)
    @classmethod
    def _validate_schedule_time(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not _UTC_TIME_RE.fullmatch(value):
            raise ValueError("Schedule times must use UTC HH:MM (24-hour) format")
        return value


class ScheduleResponse(BaseModel):
    """Schedule with 14 UTC HH:MM fields. Returned for user and mapping schedules."""

    mon_start_utc: str | None = None
    mon_end_utc: str | None = None
    tue_start_utc: str | None = None
    tue_end_utc: str | None = None
    wed_start_utc: str | None = None
    wed_end_utc: str | None = None
    thu_start_utc: str | None = None
    thu_end_utc: str | None = None
    fri_start_utc: str | None = None
    fri_end_utc: str | None = None
    sat_start_utc: str | None = None
    sat_end_utc: str | None = None
    sun_start_utc: str | None = None
    sun_end_utc: str | None = None
