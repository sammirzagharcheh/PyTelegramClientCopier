"""API tests: message-index list and UTC timestamp normalization for the UI."""

from __future__ import annotations

import asyncio

import pytest

from app.db.gateway import get_db_connection
from app.web.routers.message_index import _normalize_sqlite_utc_for_json


def _run_async(coro):
    return asyncio.run(coro)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        ("", ""),
        ("2020-06-15 18:45:30", "2020-06-15T18:45:30Z"),
        ("2020-06-15T18:45:30+00:00", "2020-06-15T18:45:30+00:00"),
        ("2020-06-15T18:45:30Z", "2020-06-15T18:45:30Z"),
    ],
)
def test_normalize_sqlite_utc_for_json(raw, expected):
    assert _normalize_sqlite_utc_for_json(raw) == expected


def test_message_index_returns_sqlite_datetime_as_z_suffixed_iso(api_client, user_token):
    """Legacy SQLite UTC strings must be normalized so JS Date parses as UTC."""

    async def seed():
        db = await get_db_connection()
        await db.execute(
            "INSERT INTO dest_message_index "
            "(user_id, source_chat_id, source_msg_id, dest_chat_id, dest_msg_id, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (1, 10, 9001, 20, 7001, "2035-03-08 14:30:00"),
        )
        await db.commit()
        await db.close()

    _run_async(seed())

    r = api_client.get(
        "/api/message-index?page=1&page_size=50",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    match = next(
        (x for x in data["items"] if x["source_msg_id"] == 9001),
        None,
    )
    assert match is not None
    assert match["updated_at"] == "2035-03-08T14:30:00Z"


def test_message_index_passes_through_python_utc_iso(api_client, user_token):
    iso = "2035-03-09T16:00:00+00:00"

    async def seed():
        db = await get_db_connection()
        await db.execute(
            "INSERT INTO dest_message_index "
            "(user_id, source_chat_id, source_msg_id, dest_chat_id, dest_msg_id, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (1, 10, 9002, 20, 7002, iso),
        )
        await db.commit()
        await db.close()

    _run_async(seed())

    r = api_client.get(
        "/api/message-index?page=1&page_size=50",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 200
    match = next(
        (x for x in r.json()["items"] if x["source_msg_id"] == 9002),
        None,
    )
    assert match is not None
    assert match["updated_at"] == iso
