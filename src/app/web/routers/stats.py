"""Dashboard stats API - user-scoped statistics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from app.db.mongo import get_mongo_db
from app.web.deps import CurrentUser, Db

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/dashboard")
async def get_dashboard_stats(user: CurrentUser, db: Db) -> dict:
    """Dashboard statistics for the current user."""
    current_user_id = int(user["id"])
    now = datetime.now(timezone.utc)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    # Last 7 calendar days: (today - 6 days) 00:00 UTC through end of today
    start_7d_ts = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    # Prev 7 days for trend: (today - 13 days) 00:00 through (today - 7 days) 00:00
    start_14d_ts = (now - timedelta(days=13)).replace(hour=0, minute=0, second=0, microsecond=0)
    start_prev_end = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)

    # SQLite: account status counts
    account_status: dict[str, int] = {}
    async with db.execute(
        "SELECT status, COUNT(*) FROM telegram_accounts WHERE user_id = ? GROUP BY status",
        (current_user_id,),
    ) as cur:
        async for row in cur:
            account_status[row[0] or "unknown"] = row[1]

    # SQLite: mappings total and enabled
    mappings_total = 0
    mappings_enabled = 0
    async with db.execute(
        "SELECT COUNT(*), SUM(CASE WHEN enabled = 1 THEN 1 ELSE 0 END) "
        "FROM channel_mappings WHERE user_id = ?",
        (current_user_id,),
    ) as cur:
        row = await cur.fetchone()
        if row:
            mappings_total = row[0] or 0
            mappings_enabled = row[1] or 0

    # MongoDB: message stats (graceful fallback if Mongo unavailable)
    messages_last_7d = 0
    messages_prev_7d = 0
    messages_by_day: list[dict[str, str | int]] = []
    status_breakdown: list[dict[str, str | int]] = []

    try:
        mongo_db = get_mongo_db()
        match = {"user_id": current_user_id, "timestamp": {"$gte": start_7d_ts, "$lte": today_end}}
        match_prev = {"user_id": current_user_id, "timestamp": {"$gte": start_14d_ts, "$lt": start_prev_end}}

        messages_last_7d = await mongo_db.message_logs.count_documents(match)
        messages_prev_7d = await mongo_db.message_logs.count_documents(match_prev)

        # Single $facet aggregation for by_day + status_breakdown
        pipeline = [
            {"$match": match},
            {
                "$facet": {
                    "by_day": [
                        {
                            "$group": {
                                "_id": {
                                    "$dateToString": {
                                        "format": "%Y-%m-%d",
                                        "date": "$timestamp",
                                        "timezone": "UTC",
                                    }
                                },
                                "count": {"$sum": 1},
                            }
                        },
                        {"$sort": {"_id": 1}},
                    ],
                    "by_status": [
                        {"$group": {"_id": {"$ifNull": ["$status", "unknown"]}, "count": {"$sum": 1}}},
                    ],
                }
            },
        ]
        agg_by_day: dict[str, int] = {}
        async for doc in mongo_db.message_logs.aggregate(pipeline):
            for d in doc.get("by_day", []):
                day = d.get("_id")
                if day:
                    agg_by_day[day] = d["count"]
            for d in doc.get("by_status", []):
                status_breakdown.append({"status": d["_id"], "count": d["count"]})

        for i in range(7):
            d = (now - timedelta(days=6 - i)).strftime("%Y-%m-%d")
            messages_by_day.append({"date": d, "count": agg_by_day.get(d, 0)})
    except Exception:
        pass  # Keep defaults on Mongo error

    return {
        "messages_last_7d": messages_last_7d,
        "messages_prev_7d": messages_prev_7d,
        "messages_by_day": messages_by_day,
        "status_breakdown": status_breakdown,
        "account_status": account_status,
        "mappings_total": mappings_total,
        "mappings_enabled": mappings_enabled,
        "accounts_total": sum(account_status.values()),
    }
