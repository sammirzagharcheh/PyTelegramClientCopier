"""Detect stale worker heartbeats and notify user-configured alert webhooks."""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone

from app.db.gateway import DbConnection

from app.services.http_notify import post_json_webhook

logger = logging.getLogger(__name__)

STALE_HEARTBEAT_SECONDS = 120
ALERT_COOLDOWN_SECONDS = 3600
_last_alert_at: dict[str, float] = {}


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _parse_iso_utc(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        t = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(t)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


async def _list_alert_webhooks(db: DbConnection, user_id: int) -> list[tuple[str, str | None]]:
    async with db.execute(
        "SELECT url, secret FROM user_alert_webhooks WHERE user_id = ? AND enabled = 1",
        (user_id,),
    ) as cur:
        return [(r[0], r[1]) for r in await cur.fetchall()]


async def check_stale_workers_and_alert(db: DbConnection) -> int:
    """Return number of alert payloads sent (one per user webhook target per stale worker)."""
    now = datetime.now(timezone.utc)
    sent = 0
    async with db.execute(
        "SELECT worker_id, user_id, account_id, pid, last_heartbeat_at, created_at FROM worker_registry"
    ) as cur:
        rows = await cur.fetchall()
    for worker_id, user_id, account_id, pid, last_hb, created_at in rows:
        if not _pid_alive(int(pid)):
            continue
        hb_dt = _parse_iso_utc(last_hb) if last_hb else None
        if hb_dt is None:
            hb_dt = _parse_iso_utc(str(created_at)) if created_at else None
        if hb_dt is None:
            continue
        age = (now - hb_dt).total_seconds()
        if age <= STALE_HEARTBEAT_SECONDS:
            continue
        key = f"{worker_id}:stale_hb"
        now_m = time.monotonic()
        if _last_alert_at.get(key, 0) + ALERT_COOLDOWN_SECONDS > now_m:
            continue
        hooks = await _list_alert_webhooks(db, int(user_id))
        if not hooks:
            continue
        payload = {
            "type": "worker_stale_heartbeat",
            "worker_id": worker_id,
            "user_id": user_id,
            "account_id": account_id,
            "pid": pid,
            "last_heartbeat_at": last_hb,
            "age_seconds": int(age),
        }
        for url, secret in hooks:
            await post_json_webhook(url, secret, payload)
            sent += 1
        _last_alert_at[key] = now_m
        logger.warning(
            "Stale worker heartbeat: worker_id=%s user_id=%s account_id=%s age_s=%d",
            worker_id,
            user_id,
            account_id,
            int(age),
        )
    return sent
