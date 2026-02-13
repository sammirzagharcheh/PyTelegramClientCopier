"""Message index (dest_message_index) API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.web.deps import CurrentUser, Db

router = APIRouter(prefix="/message-index", tags=["message-index"])


@router.get("")
async def list_message_index(
    db: Db,
    user: CurrentUser,
    user_id: int | None = None,
    source_chat_id: int | None = None,
    dest_chat_id: int | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """List dest_message_index entries. Users see own; admins can filter by user_id."""
    offset = (page - 1) * page_size
    current_user_id = int(user["id"])
    if user["role"] == "admin" and user_id is not None:
        actual_user = int(user_id)
    elif user["role"] != "admin":
        actual_user = current_user_id
    else:
        actual_user = None
    query = """SELECT user_id, source_chat_id, source_msg_id, dest_chat_id, dest_msg_id
               FROM dest_message_index WHERE 1=1"""
    params: list = []
    if actual_user is not None:
        query += " AND user_id = ?"
        params.append(actual_user)
    if source_chat_id is not None:
        query += " AND source_chat_id = ?"
        params.append(source_chat_id)
    if dest_chat_id is not None:
        query += " AND dest_chat_id = ?"
        params.append(dest_chat_id)
    query += " ORDER BY source_chat_id, source_msg_id LIMIT ? OFFSET ?"
    params.extend([page_size, offset])
    async with db.execute(query, params) as cur:
        rows = await cur.fetchall()
    count_query = "SELECT COUNT(*) FROM dest_message_index WHERE 1=1"
    count_params = []
    if actual_user is not None:
        count_query += " AND user_id = ?"
        count_params.append(actual_user)
    if source_chat_id is not None:
        count_query += " AND source_chat_id = ?"
        count_params.append(source_chat_id)
    if dest_chat_id is not None:
        count_query += " AND dest_chat_id = ?"
        count_params.append(dest_chat_id)
    async with db.execute(count_query, count_params) as cur:
        total = (await cur.fetchone())[0]
    # Non-admin: server-side post-filter to never return other users' data
    if user["role"] != "admin":
        rows = [r for r in rows if r[0] is not None and int(r[0]) == current_user_id]
    total_pages = max(1, (total + page_size - 1) // page_size) if total else 1
    return {
        "items": [
            {
                "user_id": r[0],
                "source_chat_id": r[1],
                "source_msg_id": r[2],
                "dest_chat_id": r[3],
                "dest_msg_id": r[4],
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }
