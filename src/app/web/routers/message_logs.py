"""Message logs (MongoDB) API routes."""

from __future__ import annotations

import json
import traceback
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import OperationFailure, ServerSelectionTimeoutError

from app.db.mongo import get_mongo_db
from app.web.deps import CurrentUser

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
        if user["role"] != "admin" or user_id is not None:
            match["user_id"] = user_id if user["role"] == "admin" and user_id is not None else user["id"]
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
        async for doc in cursor:
            ts = doc.get("timestamp")
            items.append({
                "user_id": doc.get("user_id"),
                "source_chat_id": doc.get("source_chat_id"),
                "source_msg_id": doc.get("source_msg_id"),
                "dest_chat_id": doc.get("dest_chat_id"),
                "dest_msg_id": doc.get("dest_msg_id"),
                "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                "status": doc.get("status"),
            })
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
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
