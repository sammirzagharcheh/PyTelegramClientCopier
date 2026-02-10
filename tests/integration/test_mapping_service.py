import pytest

from app.db.sqlite import init_sqlite, get_sqlite
from app.services.mapping_service import list_enabled_mappings


@pytest.mark.asyncio
async def test_list_enabled_mappings_with_filters(tmp_path):
    db_path = tmp_path / "test.db"
    from app.config import settings

    settings.sqlite_path = str(db_path)
    await init_sqlite()
    db = await get_sqlite()

    await db.execute(
        "INSERT INTO users (email, role, status) VALUES (?, ?, ?)",
        ("user@example.com", "user", "active"),
    )
    await db.execute(
        "INSERT INTO users (email, role, status) VALUES (?, ?, ?)",
        ("other@example.com", "user", "active"),
    )
    await db.execute(
        "INSERT INTO channel_mappings (user_id, source_chat_id, dest_chat_id, enabled) "
        "VALUES (?, ?, ?, ?)",
        (1, 111, 222, 1),
    )
    await db.execute(
        "INSERT INTO channel_mappings (user_id, source_chat_id, dest_chat_id, enabled) "
        "VALUES (?, ?, ?, ?)",
        (2, 333, 444, 1),
    )
    await db.execute(
        "INSERT INTO mapping_filters (mapping_id, include_text, exclude_text, media_types, regex_pattern) "
        "VALUES (?, ?, ?, ?, ?)",
        (1, "hello", None, "text", None),
    )
    await db.execute(
        "INSERT INTO mapping_filters (mapping_id, include_text, exclude_text, media_types, regex_pattern) "
        "VALUES (?, ?, ?, ?, ?)",
        (1, "world", None, "text", None),
    )
    await db.execute(
        "INSERT INTO mapping_filters (mapping_id, include_text, exclude_text, media_types, regex_pattern) "
        "VALUES (?, ?, ?, ?, ?)",
        (2, "other", None, "text", None),
    )
    await db.commit()

    mappings = list(await list_enabled_mappings(db, user_id=1))
    assert len(mappings) == 1
    assert mappings[0].source_chat_id == 111
    assert {f.include_text for f in mappings[0].filters} == {"hello", "world"}
