"""Dashboard stats API - user-scoped statistics."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from app.db.mongo import get_mongo_db
from app.web.deps import CurrentUser, Db

router = APIRouter(prefix="/stats", tags=["stats"])
logger = logging.getLogger(__name__)


def _ts_range_match(start_ts: datetime, end_ts: datetime) -> dict:
    """Mongo match that supports timestamp stored as Date or ISO-like string."""
    ts_expr = {
        "$convert": {
            "input": "$timestamp",
            "to": "date",
            "onError": None,
            "onNull": None,
        }
    }
    return {
        "$expr": {
            "$and": [
                {"$ne": [ts_expr, None]},
                {"$gte": [ts_expr, start_ts]},
                {"$lte": [ts_expr, end_ts]},
            ]
        }
    }


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
    messages_by_day: list[dict[str, str | int]] = [
        {"date": (now - timedelta(days=6 - i)).strftime("%Y-%m-%d"), "count": 0}
        for i in range(7)
    ]
    status_breakdown: list[dict[str, str | int]] = []
    webhook_attempts_last_7d = 0
    webhook_attempts_prev_7d = 0
    webhook_success_last_7d = 0
    webhook_failed_last_7d = 0
    webhook_by_day: list[dict[str, str | int]] = [
        {
            "date": (now - timedelta(days=6 - i)).strftime("%Y-%m-%d"),
            "success": 0,
            "failed": 0,
        }
        for i in range(7)
    ]
    top_failing_mappings: list[dict[str, str | int]] = []
    webhook_failure_reasons: list[dict[str, str | int]] = []
    unmapped_source_chats: list[dict[str, str | int]] = []

    try:
        mongo_db = get_mongo_db()
        match = {"user_id": current_user_id, **_ts_range_match(start_7d_ts, today_end)}
        match_prev = {
            "user_id": current_user_id,
            "$expr": {
                "$and": [
                    {
                        "$ne": [
                            {
                                "$convert": {
                                    "input": "$timestamp",
                                    "to": "date",
                                    "onError": None,
                                    "onNull": None,
                                }
                            },
                            None,
                        ]
                    },
                    {
                        "$gte": [
                            {
                                "$convert": {
                                    "input": "$timestamp",
                                    "to": "date",
                                    "onError": None,
                                    "onNull": None,
                                }
                            },
                            start_14d_ts,
                        ]
                    },
                    {
                        "$lt": [
                            {
                                "$convert": {
                                    "input": "$timestamp",
                                    "to": "date",
                                    "onError": None,
                                    "onNull": None,
                                }
                            },
                            start_prev_end,
                        ]
                    },
                ]
            },
        }

        messages_last_7d = await mongo_db.message_logs.count_documents(match)
        messages_prev_7d = await mongo_db.message_logs.count_documents(match_prev)
        match_webhook = {"user_id": current_user_id, "timestamp": {"$gte": start_7d_ts, "$lte": today_end}}
        match_webhook_prev = {"user_id": current_user_id, "timestamp": {"$gte": start_14d_ts, "$lt": start_prev_end}}
        webhook_attempts_last_7d = await mongo_db.webhook_logs.count_documents(match_webhook)
        webhook_attempts_prev_7d = await mongo_db.webhook_logs.count_documents(match_webhook_prev)

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
                                        "date": {
                                            "$convert": {
                                                "input": "$timestamp",
                                                "to": "date",
                                                "onError": None,
                                                "onNull": None,
                                            }
                                        },
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

        pipeline_webhook = [
            {"$match": match_webhook},
            {"$group": {"_id": {"$ifNull": ["$success", False]}, "count": {"$sum": 1}}},
        ]
        async for doc in mongo_db.webhook_logs.aggregate(pipeline_webhook):
            if bool(doc.get("_id")):
                webhook_success_last_7d = int(doc.get("count", 0))
            else:
                webhook_failed_last_7d = int(doc.get("count", 0))

        webhook_by_day_map: dict[str, dict[str, int]] = {}
        pipeline_webhook_by_day = [
            {"$match": match_webhook},
            {
                "$group": {
                    "_id": {
                        "date": {
                            "$dateToString": {
                                "format": "%Y-%m-%d",
                                "date": {
                                    "$convert": {
                                        "input": "$timestamp",
                                        "to": "date",
                                        "onError": None,
                                        "onNull": None,
                                    }
                                },
                                "timezone": "UTC",
                            }
                        },
                        "success": {"$ifNull": ["$success", False]},
                    },
                    "count": {"$sum": 1},
                }
            },
        ]
        async for doc in mongo_db.webhook_logs.aggregate(pipeline_webhook_by_day):
            key = str((doc.get("_id") or {}).get("date") or "")
            if not key:
                continue
            bucket = webhook_by_day_map.setdefault(key, {"success": 0, "failed": 0})
            if bool((doc.get("_id") or {}).get("success")):
                bucket["success"] += int(doc.get("count", 0))
            else:
                bucket["failed"] += int(doc.get("count", 0))

        for i in range(7):
            d = (now - timedelta(days=6 - i)).strftime("%Y-%m-%d")
            bucket = webhook_by_day_map.get(d, {"success": 0, "failed": 0})
            webhook_by_day[i] = {
                "date": d,
                "success": bucket["success"],
                "failed": bucket["failed"],
            }

        pipeline_top_failed = [
            {"$match": {**match_webhook, "success": False}},
            {"$group": {"_id": "$mapping_id", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 5},
        ]
        top_rows: list[dict] = []
        async for doc in mongo_db.webhook_logs.aggregate(pipeline_top_failed):
            top_rows.append(doc)
        if top_rows:
            mids = [int(d.get("_id")) for d in top_rows if d.get("_id") is not None]
            mapping_name_by_id: dict[int, str] = {}
            if mids:
                placeholders = ",".join("?" for _ in mids)
                async with db.execute(
                    f"SELECT id, name, source_chat_title, dest_chat_title, source_chat_id, dest_chat_id "
                    f"FROM channel_mappings WHERE user_id = ? AND id IN ({placeholders})",
                    (current_user_id, *mids),
                ) as cur:
                    async for row in cur:
                        mid = int(row[0])
                        name_val = (row[1] or "").strip()
                        mapping_name_by_id[mid] = (
                            name_val if name_val else f"{row[2] or row[4]} → {row[3] or row[5]}"
                        )
            for d in top_rows:
                mid = int(d.get("_id"))
                top_failing_mappings.append({
                    "name": f"M{mid}",
                    "mapping_name": mapping_name_by_id.get(mid, f"Mapping {mid}"),
                    "count": int(d.get("count", 0)),
                })

        pipeline_failure_reasons = [
            {"$match": {**match_webhook, "success": False}},
            {"$project": {"status_code": "$response.status_code", "error": {"$ifNull": ["$error", ""]}}},
        ]
        reason_counts: dict[str, int] = {
            "HTTP 401": 0,
            "HTTP 403": 0,
            "HTTP 404": 0,
            "HTTP 429": 0,
            "HTTP 5xx": 0,
            "Timeout": 0,
            "Network/Connection": 0,
            "Other": 0,
        }
        async for doc in mongo_db.webhook_logs.aggregate(pipeline_failure_reasons):
            status_code = doc.get("status_code")
            err = str(doc.get("error") or "").lower()
            bucket = "Other"
            if isinstance(status_code, int):
                if status_code == 401:
                    bucket = "HTTP 401"
                elif status_code == 403:
                    bucket = "HTTP 403"
                elif status_code == 404:
                    bucket = "HTTP 404"
                elif status_code == 429:
                    bucket = "HTTP 429"
                elif 500 <= status_code <= 599:
                    bucket = "HTTP 5xx"
            if bucket == "Other":
                if "timeout" in err:
                    bucket = "Timeout"
                elif any(x in err for x in ("connection", "connect", "network", "dns", "refused", "unreachable")):
                    bucket = "Network/Connection"
            reason_counts[bucket] += 1
        webhook_failure_reasons = [
            {"name": name, "count": count}
            for name, count in reason_counts.items()
            if count > 0
        ]

        pipeline_unmapped_sources = [
            {
                "$match": {
                    "user_id": current_user_id,
                    **_ts_range_match(start_7d_ts, today_end),
                    "message": {"$regex": "has no mapping"},
                }
            },
            {
                "$project": {
                    "chat_match": {
                        "$regexFind": {
                            "input": "$message",
                            "regex": "chat_id=([-0-9]+)",
                        }
                    }
                }
            },
            {
                "$project": {
                    "chat_id": {
                        "$ifNull": [
                            {"$arrayElemAt": ["$chat_match.captures", 0]},
                            "unknown",
                        ]
                    }
                }
            },
            {"$group": {"_id": "$chat_id", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10},
        ]
        async for doc in mongo_db.worker_logs.aggregate(pipeline_unmapped_sources):
            unmapped_source_chats.append(
                {
                    "chat_id": str(doc.get("_id", "unknown")),
                    "count": int(doc.get("count", 0)),
                }
            )

        for i in range(7):
            d = (now - timedelta(days=6 - i)).strftime("%Y-%m-%d")
            messages_by_day[i] = {"date": d, "count": agg_by_day.get(d, 0)}
    except Exception as exc:
        logger.exception("user dashboard aggregation failed user_id=%s: %s", current_user_id, exc)

    payload = {
        "messages_last_7d": messages_last_7d,
        "messages_prev_7d": messages_prev_7d,
        "messages_by_day": messages_by_day,
        "status_breakdown": status_breakdown,
        "account_status": account_status,
        "mappings_total": mappings_total,
        "mappings_enabled": mappings_enabled,
        "accounts_total": sum(account_status.values()),
        "webhook_attempts_last_7d": webhook_attempts_last_7d,
        "webhook_attempts_prev_7d": webhook_attempts_prev_7d,
        "webhook_success_last_7d": webhook_success_last_7d,
        "webhook_failed_last_7d": webhook_failed_last_7d,
        "webhook_success_rate": round(
            (webhook_success_last_7d / webhook_attempts_last_7d) * 100, 1
        )
        if webhook_attempts_last_7d > 0
        else 0.0,
        "webhook_by_day": webhook_by_day,
        "top_failing_mappings": top_failing_mappings,
        "webhook_failure_reasons": webhook_failure_reasons,
        "unmapped_source_chats": unmapped_source_chats,
    }
    logger.info(
        "user dashboard payload user_id=%s top_failing=%d failure_reasons=%d",
        current_user_id,
        len(top_failing_mappings),
        len(webhook_failure_reasons),
    )
    return payload
