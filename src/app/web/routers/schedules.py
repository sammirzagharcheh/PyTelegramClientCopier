"""Schedule API routes: user schedule and mapping schedule overrides."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.services.mapping_service import WEEKDAY_COLS
from app.web.deps import CurrentUser, Db
from app.web.schemas.schedules import ScheduleResponse, ScheduleUpdate

router = APIRouter(prefix="/users", tags=["schedules"])


def _schedule_row_to_dict(row: tuple | None) -> dict:
    """Convert DB row (14 cols) to response dict."""
    if not row:
        return {c: None for c in WEEKDAY_COLS}
    return dict(zip(WEEKDAY_COLS, row))


async def _get_user_schedule(db, user_id: int) -> dict:
    cols = ", ".join(WEEKDAY_COLS)
    async with db.execute(
        f"SELECT {cols} FROM user_schedules WHERE user_id = ?",
        (user_id,),
    ) as cur:
        row = await cur.fetchone()
    return _schedule_row_to_dict(row)


@router.get("/me/schedule", response_model=ScheduleResponse)
async def get_user_schedule(db: Db, user: CurrentUser) -> dict:
    """Get current user's default schedule. Returns UTC HH:MM. Null = unrestricted for that slot."""
    return await _get_user_schedule(db, user["id"])


@router.patch("/me/schedule", response_model=ScheduleResponse)
async def update_user_schedule(
    data: ScheduleUpdate,
    db: Db,
    user: CurrentUser,
) -> dict:
    """Update current user's default schedule. Accepts UTC HH:MM strings."""
    cols = ", ".join(WEEKDAY_COLS)
    placeholders = ", ".join("?" for _ in WEEKDAY_COLS)
    upsert_cols = ", ".join(f"{c} = excluded.{c}" for c in WEEKDAY_COLS)
    model_dict = data.model_dump()
    values = [model_dict.get(c) for c in WEEKDAY_COLS]
    await db.execute(
        f"""INSERT INTO user_schedules (user_id, {cols})
            VALUES (?, {placeholders})
            ON CONFLICT(user_id) DO UPDATE SET {upsert_cols}""",
        (user["id"], *values),
    )
    await db.commit()
    return await _get_user_schedule(db, user["id"])
