"""API tests: dest_message_index cleanup on mapping delete/update."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

from app.db.gateway import get_db_connection, init_db


def _run_async(coro):
    return asyncio.run(coro)


def test_delete_mapping_removes_dest_message_index(api_client, user_token):
    async def seed_index():
        await init_db()
        db = await get_db_connection()
        await db.execute(
            "INSERT INTO dest_message_index "
            "(user_id, source_chat_id, source_msg_id, dest_chat_id, dest_msg_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (1, 10, 1001, 20, 5001),
        )
        await db.commit()
        await db.close()

    _run_async(seed_index())

    with patch("app.web.routers.mappings.restart_workers_for_mapping"):
        r = api_client.delete(
            "/api/mappings/1",
            headers={"Authorization": f"Bearer {user_token}"},
        )
    assert r.status_code == 200

    async def count_rows():
        db = await get_db_connection()
        async with db.execute("SELECT COUNT(*) FROM dest_message_index WHERE user_id = 1") as cur:
            n = (await cur.fetchone())[0]
        await db.close()
        return n

    assert _run_async(count_rows()) == 0


def test_delete_mapping_removes_index_with_alternate_source_chat_id(api_client, user_token):
    """Index may store legacy source id while mapping uses full channel id."""
    full_src = -1001234567890
    legacy_src = -1234567890
    dest = 888888

    async def seed():
        await init_db()
        db = await get_db_connection()
        await db.execute(
            "INSERT INTO channel_mappings (user_id, source_chat_id, dest_chat_id, enabled) "
            "VALUES (?, ?, ?, ?)",
            (1, full_src, dest, 1),
        )
        await db.execute(
            "INSERT INTO dest_message_index "
            "(user_id, source_chat_id, source_msg_id, dest_chat_id, dest_msg_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (1, legacy_src, 42, dest, 99),
        )
        await db.commit()
        async with db.execute("SELECT id FROM channel_mappings WHERE source_chat_id = ?", (full_src,)) as cur:
            mid = (await cur.fetchone())[0]
        await db.close()
        return mid

    mapping_id = _run_async(seed())

    with patch("app.web.routers.mappings.restart_workers_for_mapping"):
        r = api_client.delete(
            f"/api/mappings/{mapping_id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
    assert r.status_code == 200

    async def count_rows():
        db = await get_db_connection()
        async with db.execute(
            "SELECT COUNT(*) FROM dest_message_index WHERE user_id = 1 AND dest_chat_id = ?",
            (dest,),
        ) as cur:
            n = (await cur.fetchone())[0]
        await db.close()
        return n

    assert _run_async(count_rows()) == 0


def test_patch_mapping_source_clears_dest_message_index(api_client, user_token):
    async def seed_index():
        await init_db()
        db = await get_db_connection()
        await db.execute(
            "INSERT INTO dest_message_index "
            "(user_id, source_chat_id, source_msg_id, dest_chat_id, dest_msg_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (1, 10, 2002, 20, 6002),
        )
        await db.commit()
        await db.close()

    _run_async(seed_index())

    with patch("app.web.routers.mappings.restart_workers_for_mapping"):
        r = api_client.patch(
            "/api/mappings/1",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"source_chat_id": 11},
        )
    assert r.status_code == 200

    async def count_rows():
        db = await get_db_connection()
        async with db.execute(
            "SELECT COUNT(*) FROM dest_message_index WHERE user_id = 1 AND dest_chat_id = 20"
        ) as cur:
            n = (await cur.fetchone())[0]
        await db.close()
        return n

    assert _run_async(count_rows()) == 0


def test_patch_mapping_dest_clears_dest_message_index(api_client, user_token):
    async def seed_index():
        await init_db()
        db = await get_db_connection()
        await db.execute(
            "INSERT INTO dest_message_index "
            "(user_id, source_chat_id, source_msg_id, dest_chat_id, dest_msg_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (1, 10, 3003, 20, 7003),
        )
        await db.commit()
        await db.close()

    _run_async(seed_index())

    with patch("app.web.routers.mappings.restart_workers_for_mapping"):
        r = api_client.patch(
            "/api/mappings/1",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"dest_chat_id": 21},
        )
    assert r.status_code == 200

    async def count_rows():
        db = await get_db_connection()
        async with db.execute(
            "SELECT COUNT(*) FROM dest_message_index WHERE user_id = 1 AND source_chat_id = 10 AND dest_chat_id = 20"
        ) as cur:
            n = (await cur.fetchone())[0]
        await db.close()
        return n

    assert _run_async(count_rows()) == 0


def test_purge_orphan_dest_message_index_removes_stale_rows(monkeypatch):
    from app.db.message_index_cleanup import purge_orphan_dest_message_index

    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "t.db"
        async def setup():
            await init_db()
            db = await get_db_connection()
            await db.execute(
                "INSERT INTO users (email, role, status, password_hash, name) VALUES (?, ?, ?, ?, ?)",
                ("x@test.com", "user", "active", "x", "X"),
            )
            await db.execute(
                "INSERT INTO channel_mappings (user_id, source_chat_id, dest_chat_id, enabled) "
                "VALUES (?, ?, ?, ?)",
                (1, 10, 20, 1),
            )
            await db.execute(
                "INSERT INTO dest_message_index "
                "(user_id, source_chat_id, source_msg_id, dest_chat_id, dest_msg_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (1, 10, 1, 20, 100),
            )
            await db.execute(
                "INSERT INTO dest_message_index "
                "(user_id, source_chat_id, source_msg_id, dest_chat_id, dest_msg_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (1, 99, 2, 99, 200),
            )
            await db.commit()
            await db.close()

        _run_async(setup())

        async def run_purge():
            db = await get_db_connection()
            try:
                return await purge_orphan_dest_message_index(db, dry_run=False)
            finally:
                await db.close()

        removed = _run_async(run_purge())
        assert removed == 1

        async def count_all():
            db = await get_db_connection()
            async with db.execute("SELECT COUNT(*) FROM dest_message_index") as cur:
                n = (await cur.fetchone())[0]
            await db.close()
            return n

        assert _run_async(count_all()) == 1
