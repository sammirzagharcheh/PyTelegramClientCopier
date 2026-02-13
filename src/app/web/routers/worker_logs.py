"""Worker logs (MongoDB) API routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import OperationFailure, ServerSelectionTimeoutError

from app.db.mongo import get_mongo_db
from app.web.deps import CurrentUser

router = APIRouter(prefix="/worker-logs", tags=["worker-logs"])


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
async def list_worker_logs(
    user: CurrentUser,
    user_id: int | None = None,
    account_id: int | None = None,
    level: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """List worker logs from MongoDB. Users see own; admins can filter."""
    try:
        mongo_db = get_mongo_db()
        match: dict = {}
        current_user_id = int(user["id"])
        # Non-admin: always restrict to own data
        if user["role"] != "admin":
            match["user_id"] = current_user_id
        # Admin: restrict only when user_id query param is provided
        elif user_id is not None:
            match["user_id"] = int(user_id)
        if account_id is not None:
            match["account_id"] = account_id
        if level is not None:
            match["level"] = level.upper()
        if date_from or date_to:
            match["timestamp"] = {}
            if date_from:
                match["timestamp"]["$gte"] = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
            if date_to:
                match["timestamp"]["$lte"] = datetime.fromisoformat(date_to.replace("Z", "+00:00"))

        pipeline = [{"$match": match}]
        count_cursor = mongo_db.worker_logs.aggregate(
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
        cursor = mongo_db.worker_logs.aggregate(pipeline)
        items = []
        async for doc in cursor:
            ts = doc.get("timestamp")
            items.append({
                "user_id": doc.get("user_id"),
                "account_id": doc.get("account_id"),
                "level": doc.get("level"),
                "message": doc.get("message"),
                "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
            })
        # Non-admin: server-side post-filter to never return other users' data
        if user["role"] != "admin":
            items = [it for it in items if it.get("user_id") is not None and int(it["user_id"]) == current_user_id]
            total = await mongo_db.worker_logs.count_documents(match)
        total_pages = max(1, (total + page_size - 1) // page_size) if total else 1
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
    except (OperationFailure, ServerSelectionTimeoutError) as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_mongo_error_message(e),
        ) from e
