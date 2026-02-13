"""Message logs (MongoDB) API routes."""

from __future__ import annotations

import json
import traceback
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import OperationFailure, ServerSelectionTimeoutError

from app.db.mongo import get_mongo_db
from app.web.deps import CurrentUser, Db

router = APIRouter(prefix="/message-logs", tags=["message-logs"])


def _mongo_error_message(e: Exception) -> str:
    """User-friendly message for MongoDB connection/auth errors."""
    err = str(e).lower()
    if "auth required" in err or "unauthorized" in err:
        return (
            "MongoDB authentication required. Configure MongoDB URI with credentials "
            "in Admin Settings (e.g. mongodb://user:pass@host/db)."
        )
    if "timeout" in err or "server selection" in err:
        return "MongoDB connection failed. Check URI and network in Admin Settings."
    return f"MongoDB error: {e}"


@router.get("")
async def list_message_logs(
    user: CurrentUser,
    db: Db,
    user_id: int | None = None,
    source_chat_id: int | None = None,
    dest_chat_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """List message logs from MongoDB. Users see own; admins can filter."""
    # #region agent log
    try:
        # #endregion agent log
        mongo_db = get_mongo_db()
        match: dict = {}
        current_user_id = int(user["id"])
        # Non-admin: always restrict to own data
        if user["role"] != "admin":
            match["user_id"] = current_user_id
        # Admin: restrict only when user_id query param is provided
        elif user_id is not None:
            match["user_id"] = int(user_id)
        if source_chat_id is not None:
            match["source_chat_id"] = source_chat_id
        if dest_chat_id is not None:
            match["dest_chat_id"] = dest_chat_id
        if date_from or date_to:
            match["timestamp"] = {}
            if date_from:
                match["timestamp"]["$gte"] = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
            if date_to:
                match["timestamp"]["$lte"] = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
        pipeline = [{"$match": match}]
        count_cursor = mongo_db.message_logs.aggregate(
            pipeline + [{"$count": "total"}]
        )
        total = 0
        async for doc in count_cursor:
            total = doc["total"]
            break
        pipeline.extend([
            {"$sort": {"timestamp": -1}},
            {"$skip": (page - 1) * page_size},
            {"$limit": page_size},
        ])
        cursor = mongo_db.message_logs.aggregate(pipeline)
        items = []
        need_fallback: set[tuple[int, int, int]] = set()
        async for doc in cursor:
            ts = doc.get("timestamp")
            uid = doc.get("user_id")
            src_id = doc.get("source_chat_id")
            dest_id = doc.get("dest_chat_id")
            src_title = doc.get("source_chat_title") or None
            dest_title = doc.get("dest_chat_title") or None
            if (src_title is None or src_title == "" or dest_title is None or dest_title == "") and uid is not None and src_id is not None and dest_id is not None:
                need_fallback.add((uid, src_id, dest_id))
            items.append({
                "user_id": uid,
                "source_chat_id": src_id,
                "source_msg_id": doc.get("source_msg_id"),
                "dest_chat_id": dest_id,
                "dest_msg_id": doc.get("dest_msg_id"),
                "source_chat_title": src_title or None,
                "dest_chat_title": dest_title or None,
                "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                "status": doc.get("status"),
            })
        if need_fallback:
            title_map: dict[tuple[int, int, int], tuple[str | None, str | None]] = {}
            for uid, src_id, dest_id in need_fallback:
                async with db.execute(
                    "SELECT source_chat_title, dest_chat_title FROM channel_mappings "
                    "WHERE user_id = ? AND source_chat_id = ? AND dest_chat_id = ? LIMIT 1",
                    (uid, src_id, dest_id),
                ) as cur:
                    row = await cur.fetchone()
                if row:
                    st, dt = row[0] or None, row[1] or None
                    title_map[(uid, src_id, dest_id)] = (st, dt)
            for it in items:
                key = (it["user_id"], it["source_chat_id"], it["dest_chat_id"])
                if key in title_map and (not it.get("source_chat_title") or not it.get("dest_chat_title")):
                    st, dt = title_map[key]
                    if not it.get("source_chat_title"):
                        it["source_chat_title"] = st
                    if not it.get("dest_chat_title"):
                        it["dest_chat_title"] = dt
        # Non-admin: server-side post-filter to never return other users' data
        if user["role"] != "admin":
            items = [it for it in items if it.get("user_id") is not None and int(it["user_id"]) == current_user_id]
            total = await mongo_db.message_logs.count_documents(match)
        total_pages = max(1, (total + page_size - 1) // page_size) if total else 1
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
    except (OperationFailure, ServerSelectionTimeoutError) as e:
        # #region agent log
        try:
            log_entry = {
                "id": "message_logs_mongo_error",
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
                "location": "message_logs.py:list_message_logs",
                "message": "mongo_auth_or_connection_error",
                "data": {
                    "error_type": type(e).__name__,
                    "error_str": str(e),
                },
                "runId": "post-fix",
                "hypothesisId": "mongo_auth",
            }
            log_path = Path(r"d:\Ongoing Projects\TelegramClientCopier\.cursor\debug.log")
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, default=str) + "\n")
        except Exception:
            pass
        # #endregion agent log
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_mongo_error_message(e),
        ) from e
    except Exception as e:
        # #region agent log
        try:
            log_entry = {
                "id": "message_logs_error",
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
                "location": "message_logs.py:list_message_logs",
                "message": "message_logs_unexpected_error",
                "data": {
                    "error_type": type(e).__name__,
                    "error_str": str(e),
                    "traceback": traceback.format_exc(),
                },
                "runId": "post-fix",
                "hypothesisId": "unexpected",
            }
            log_path = Path(r"d:\Ongoing Projects\TelegramClientCopier\.cursor\debug.log")
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, default=str) + "\n")
        except Exception:
            pass
        # #endregion agent log
        raise
