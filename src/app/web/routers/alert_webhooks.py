"""User alert webhooks (worker health notifications)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import AnyHttpUrl, BaseModel

from app.utils.time import normalize_utc_iso_for_json
from app.web.deps import CurrentUser, Db, WriterUser

router = APIRouter(prefix="/users", tags=["alert-webhooks"])


class AlertWebhookCreate(BaseModel):
    url: AnyHttpUrl
    secret: str | None = None


class AlertWebhookResponse(BaseModel):
    id: int
    url: str
    enabled: bool
    created_at: str | None


@router.get("/me/alert-webhooks", response_model=list[AlertWebhookResponse])
async def list_alert_webhooks(db: Db, user: CurrentUser) -> list[dict]:
    async with db.execute(
        "SELECT id, url, enabled, created_at FROM user_alert_webhooks WHERE user_id = ? ORDER BY id",
        (user["id"],),
    ) as cur:
        rows = await cur.fetchall()
    return [
        {"id": r[0], "url": r[1], "enabled": bool(r[2]), "created_at": normalize_utc_iso_for_json(r[3])}
        for r in rows
    ]


@router.post("/me/alert-webhooks", response_model=AlertWebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_alert_webhook(
    data: AlertWebhookCreate,
    db: Db,
    user: WriterUser,
) -> dict:
    async with db.execute(
        "INSERT INTO user_alert_webhooks (user_id, url, secret, enabled) VALUES (?, ?, ?, 1) RETURNING id",
        (user["id"], str(data.url), data.secret),
    ) as cur:
        inserted = await cur.fetchone()
    await db.commit()
    if not inserted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create alert webhook",
        )
    wid = int(inserted[0])
    async with db.execute(
        "SELECT id, url, enabled, created_at FROM user_alert_webhooks WHERE id = ?",
        (wid,),
    ) as c2:
        row = await c2.fetchone()
    assert row
    return {"id": row[0], "url": row[1], "enabled": bool(row[2]), "created_at": normalize_utc_iso_for_json(row[3])}


@router.delete("/me/alert-webhooks/{webhook_id}")
async def delete_alert_webhook(
    webhook_id: int,
    db: Db,
    user: WriterUser,
) -> dict:
    await db.execute(
        "DELETE FROM user_alert_webhooks WHERE id = ? AND user_id = ?",
        (webhook_id, user["id"]),
    )
    await db.commit()
    return {"status": "ok"}
