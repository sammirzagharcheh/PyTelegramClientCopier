"""Active mapping webhook delivery logs (MongoDB) API routes."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pymongo.errors import OperationFailure, ServerSelectionTimeoutError

from app.db.mongo import get_mongo_db
from app.web.deps import CurrentUser, Db

router = APIRouter(prefix="/webhook-logs", tags=["webhook-logs"])


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
async def list_webhook_logs(
    user: CurrentUser,
    db: Db,
    user_id: int | None = None,
    mapping_id: int | None = None,
    success: bool | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """List webhook delivery logs for currently enabled mappings."""
    try:
        is_admin = user.get("role") == "admin"
        current_user_id = int(user["id"])
        query = (
            "SELECT id, user_id, source_chat_id, dest_chat_id, source_chat_title, dest_chat_title "
            "FROM channel_mappings WHERE enabled = 1"
        )
        params: list[int] = []
        if not is_admin:
            query += " AND user_id = ?"
            params.append(current_user_id)
        elif user_id is not None:
            query += " AND user_id = ?"
            params.append(int(user_id))
        if mapping_id is not None:
            query += " AND id = ?"
            params.append(int(mapping_id))
        async with db.execute(query, tuple(params)) as cur:
            rows = await cur.fetchall()
        if not rows:
            return {"items": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 1}

        mapping_meta: dict[int, dict] = {}
        enabled_ids: list[int] = []
        for row in rows:
            mid = int(row[0])
            enabled_ids.append(mid)
            mapping_meta[mid] = {
                "mapping_id": mid,
                "user_id": int(row[1]),
                "source_chat_id": int(row[2]),
                "dest_chat_id": int(row[3]),
                "source_chat_title": row[4] or None,
                "dest_chat_title": row[5] or None,
            }

        mongo_db = get_mongo_db()
        match: dict = {"mapping_id": {"$in": enabled_ids}}
        if success is not None:
            match["success"] = bool(success)
        if date_from or date_to:
            match["timestamp"] = {}
            if date_from:
                match["timestamp"]["$gte"] = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
            if date_to:
                match["timestamp"]["$lte"] = datetime.fromisoformat(date_to.replace("Z", "+00:00"))

        total = await mongo_db.webhook_logs.count_documents(match)
        cursor = (
            mongo_db.webhook_logs.find(match)
            .sort("timestamp", -1)
            .skip((page - 1) * page_size)
            .limit(page_size)
        )
        items = []
        async for doc in cursor:
            mid = int(doc.get("mapping_id") or 0)
            meta = mapping_meta.get(mid)
            if meta is None:
                continue
            ts = doc.get("timestamp")
            req = doc.get("request") or {}
            res = doc.get("response") or {}
            items.append({
                "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                "success": bool(doc.get("success")),
                "error": doc.get("error"),
                "event": doc.get("event"),
                "request_url": req.get("url"),
                "request_method": req.get("method") or "POST",
                "payload_size_bytes": req.get("payload_size_bytes"),
                "request_body_preview": req.get("body_preview"),
                "request_headers": req.get("headers") or {},
                "status_code": res.get("status_code"),
                "status_text": res.get("status_text"),
                "latency_ms": res.get("latency_ms"),
                "response_content_type": res.get("content_type"),
                "response_body": res.get("body"),
                "response_body_truncated": bool(res.get("body_truncated")),
                **meta,
            })

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
