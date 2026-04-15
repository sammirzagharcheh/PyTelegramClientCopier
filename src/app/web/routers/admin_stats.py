"""Admin dashboard stats API - system-wide statistics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from app.db.mongo import get_mongo_db
from app.web.deps import AdminUser, Db
from app.web.routers.workers import _is_process_alive, _workers

router = APIRouter(prefix="/admin/stats", tags=["admin-stats"])


@router.get("/dashboard")
async def get_admin_dashboard_stats(user: AdminUser, db: Db) -> dict:
    """Admin dashboard: system-wide statistics."""
    now = datetime.now(timezone.utc)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    # Last 7 calendar days: (today - 6 days) 00:00 UTC through end of today
    start_7d_ts = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    # Prev 7 days for trend
    start_14d_ts = (now - timedelta(days=13)).replace(hour=0, minute=0, second=0, microsecond=0)
    start_prev_end = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)

    # SQLite: users total
    users_total = 0
    async with db.execute("SELECT COUNT(*) FROM users") as cur:
        row = await cur.fetchone()
        if row:
            users_total = row[0]

    # SQLite: mappings total and enabled
    mappings_total = 0
    mappings_enabled = 0
    async with db.execute(
        "SELECT COUNT(*), SUM(CASE WHEN enabled = 1 THEN 1 ELSE 0 END) FROM channel_mappings"
    ) as cur:
        row = await cur.fetchone()
        if row:
            mappings_total = row[0] or 0
            mappings_enabled = row[1] or 0

    # SQLite: active accounts
    active_accounts = 0
    async with db.execute(
        "SELECT COUNT(*) FROM telegram_accounts WHERE status = 'active'"
    ) as cur:
        row = await cur.fetchone()
        if row:
            active_accounts = row[0]

    # Workers count (from in-memory registry)
    workers_count = sum(1 for w in _workers.values() if _is_process_alive(w))

    # MongoDB: message stats
    messages_last_7d = 0
    messages_prev_7d = 0
    messages_by_day: list[dict[str, str | int]] = []
    status_breakdown: list[dict[str, str | int]] = []
    top_mappings: list[dict[str, str | int]] = []
    worker_log_levels: list[dict[str, str | int]] = []
    webhook_attempts_last_7d = 0
    webhook_attempts_prev_7d = 0
    webhook_success_last_7d = 0
    webhook_failed_last_7d = 0
    webhook_by_day: list[dict[str, str | int]] = []
    top_failing_mappings: list[dict[str, str | int]] = []
    webhook_failure_reasons: list[dict[str, str | int]] = []

    try:
        mongo_db = get_mongo_db()
        match_7d = {"timestamp": {"$gte": start_7d_ts, "$lte": today_end}}
        match_prev = {"timestamp": {"$gte": start_14d_ts, "$lt": start_prev_end}}

        messages_last_7d = await mongo_db.message_logs.count_documents(match_7d)
        messages_prev_7d = await mongo_db.message_logs.count_documents(match_prev)
        webhook_attempts_last_7d = await mongo_db.webhook_logs.count_documents(match_7d)
        webhook_attempts_prev_7d = await mongo_db.webhook_logs.count_documents(match_prev)

        # Single $facet aggregation for by_day, status_breakdown, top_mappings
        pipeline = [
            {"$match": match_7d},
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
                    "top": [
                        {
                            "$group": {
                                "_id": {
                                    "user_id": "$user_id",
                                    "source_chat_id": "$source_chat_id",
                                    "dest_chat_id": "$dest_chat_id",
                                },
                                "count": {"$sum": 1},
                            }
                        },
                        {"$sort": {"count": -1}},
                        {"$limit": 5},
                    ],
                }
            },
        ]
        agg_by_day: dict[str, int] = {}
        top_raw: list[dict] = []
        async for doc in mongo_db.message_logs.aggregate(pipeline):
            for d in doc.get("by_day", []):
                day = d.get("_id")
                if day:
                    agg_by_day[day] = d["count"]
            for d in doc.get("by_status", []):
                status_breakdown.append({"status": d["_id"], "count": d["count"]})
            top_raw = doc.get("top", [])

        for i in range(7):
            d = (now - timedelta(days=6 - i)).strftime("%Y-%m-%d")
            messages_by_day.append({"date": d, "count": agg_by_day.get(d, 0)})

        # Batch mapping lookups: (user_id, src_id, dest_id) -> (mapping_id, mapping_name)
        mapping_map: dict[tuple[int | None, int, int], tuple[int, str]] = {}
        if top_raw:
            keys = [
                (g.get("user_id"), g.get("source_chat_id", 0), g.get("dest_chat_id", 0))
                for doc in top_raw
                for g in [doc.get("_id", {})]
            ]
            keys = [k for k in keys if k[0] is not None]
            if keys:
                placeholders = ",".join(["(?,?,?)"] * len(keys))
                params = [x for t in keys for x in t]
                async with db.execute(
                    f"SELECT id, user_id, source_chat_id, dest_chat_id, name, source_chat_title, dest_chat_title "
                    f"FROM channel_mappings WHERE (user_id, source_chat_id, dest_chat_id) IN "
                    f"(VALUES {placeholders})",
                    params,
                ) as cur:
                    async for row in cur:
                        mapping_id, uid, src_id, dest_id = row[0], row[1], row[2], row[3]
                        name_val, st, dt = row[4], row[5], row[6]
                        mapping_name = name_val if name_val else f"{st or src_id} → {dt or dest_id}"
                        mapping_map[(uid, src_id, dest_id)] = (mapping_id, mapping_name)
        for doc in top_raw:
            g = doc.get("_id", {})
            uid, src_id, dest_id = g.get("user_id"), g.get("source_chat_id", 0), g.get("dest_chat_id", 0)
            entry = mapping_map.get((uid, src_id, dest_id))
            if entry:
                mapping_id, mapping_name = entry
                bar_label = f"{uid}-{mapping_id}"
                top_mappings.append({"name": bar_label, "mapping_name": mapping_name, "count": doc["count"]})
            else:
                fallback = f"{src_id} → {dest_id}"
                top_mappings.append({"name": f"{uid}-?", "mapping_name": fallback, "count": doc["count"]})

        # worker_log_levels (last 7d)
        match_worker = {"timestamp": {"$gte": start_7d_ts, "$lte": today_end}}
        pipeline_levels = [
            {"$match": match_worker},
            {"$group": {"_id": {"$ifNull": ["$level", "INFO"]}, "count": {"$sum": 1}}},
        ]
        async for doc in mongo_db.worker_logs.aggregate(pipeline_levels):
            worker_log_levels.append({"level": doc["_id"], "count": doc["count"]})
        pipeline_webhook = [
            {"$match": match_7d},
            {"$group": {"_id": {"$ifNull": ["$success", False]}, "count": {"$sum": 1}}},
        ]
        async for doc in mongo_db.webhook_logs.aggregate(pipeline_webhook):
            if bool(doc.get("_id")):
                webhook_success_last_7d = int(doc.get("count", 0))
            else:
                webhook_failed_last_7d = int(doc.get("count", 0))

        webhook_by_day_map: dict[str, dict[str, int]] = {}
        pipeline_webhook_by_day = [
            {"$match": match_7d},
            {
                "$group": {
                    "_id": {
                        "date": {
                            "$dateToString": {
                                "format": "%Y-%m-%d",
                                "date": "$timestamp",
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
            webhook_by_day.append({
                "date": d,
                "success": bucket["success"],
                "failed": bucket["failed"],
            })

        pipeline_top_failed = [
            {"$match": {**match_7d, "success": False}},
            {"$group": {"_id": {"user_id": "$user_id", "mapping_id": "$mapping_id"}, "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 5},
        ]
        top_failed_raw: list[dict] = []
        async for doc in mongo_db.webhook_logs.aggregate(pipeline_top_failed):
            top_failed_raw.append(doc)
        if top_failed_raw:
            keys = [
                (int((d.get("_id") or {}).get("user_id")), int((d.get("_id") or {}).get("mapping_id")))
                for d in top_failed_raw
                if (d.get("_id") or {}).get("user_id") is not None and (d.get("_id") or {}).get("mapping_id") is not None
            ]
            mapping_name_by_key: dict[tuple[int, int], str] = {}
            if keys:
                placeholders = ",".join(["(?,?)"] * len(keys))
                params = [x for k in keys for x in k]
                async with db.execute(
                    f"SELECT user_id, id, name, source_chat_title, dest_chat_title, source_chat_id, dest_chat_id "
                    f"FROM channel_mappings WHERE (user_id, id) IN (VALUES {placeholders})",
                    params,
                ) as cur:
                    async for row in cur:
                        uid = int(row[0])
                        mid = int(row[1])
                        name_val = (row[2] or "").strip()
                        mapping_name_by_key[(uid, mid)] = (
                            name_val if name_val else f"{row[3] or row[5]} → {row[4] or row[6]}"
                        )
            for d in top_failed_raw:
                group = d.get("_id") or {}
                uid = int(group.get("user_id"))
                mid = int(group.get("mapping_id"))
                top_failing_mappings.append({
                    "name": f"U{uid}-M{mid}",
                    "mapping_name": mapping_name_by_key.get((uid, mid), f"User {uid} / Mapping {mid}"),
                    "count": int(d.get("count", 0)),
                })
        pipeline_failure_reasons = [
            {"$match": {**match_7d, "success": False}},
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
    except Exception:
        pass

    return {
        "users_total": users_total,
        "mappings_total": mappings_total,
        "mappings_enabled": mappings_enabled,
        "workers_count": workers_count,
        "active_accounts": active_accounts,
        "messages_last_7d": messages_last_7d,
        "messages_prev_7d": messages_prev_7d,
        "messages_by_day": messages_by_day,
        "status_breakdown": status_breakdown,
        "top_mappings": top_mappings,
        "worker_log_levels": worker_log_levels,
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
    }
