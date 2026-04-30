from __future__ import annotations

import pytest

from app.services.mapping_service import list_enabled_mappings

pytestmark = pytest.mark.postgres_parity


@pytest.mark.asyncio
async def test_list_enabled_mappings_with_filters_postgres(postgres_db):
    db = postgres_db
    cur1 = await db.execute(
        "INSERT INTO users (email, role, status) VALUES (?, ?, ?)",
        ("user@example.com", "user", "active"),
    )
    user1_id = int(cur1.lastrowid or 0)
    await db.execute(
        "INSERT INTO users (email, role, status) VALUES (?, ?, ?)",
        ("other@example.com", "user", "active"),
    )
    mapping_cur = await db.execute(
        "INSERT INTO channel_mappings (user_id, source_chat_id, dest_chat_id, enabled) VALUES (?, ?, ?, ?)",
        (user1_id, 111, 222, 1),
    )
    mapping_id = int(mapping_cur.lastrowid or 0)
    await db.execute(
        "INSERT INTO mapping_filters (mapping_id, include_text, exclude_text, media_types, regex_pattern, or_group_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (mapping_id, "hello", None, "text", None, 1),
    )
    await db.commit()

    mappings = list(await list_enabled_mappings(db, user_id=user1_id))
    assert len(mappings) == 1
    assert mappings[0].source_chat_id == 111
    assert mappings[0].filters[0].include_text == "hello"
