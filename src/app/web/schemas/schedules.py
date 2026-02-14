"""Schedule Pydantic schemas. All times in UTC HH:MM."""

from __future__ import annotations

from pydantic import BaseModel


class ScheduleSlot(BaseModel):
    """Start/end for one weekday."""

    start_utc: str | None = None  # HH:MM
    end_utc: str | None = None  # HH:MM


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
