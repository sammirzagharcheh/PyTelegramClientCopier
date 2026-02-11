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


@pytest.mark.asyncio
async def test_list_enabled_mappings_no_filters(tmp_path):
    db_path = tmp_path / "test.db"
    from app.config import settings

    settings.sqlite_path = str(db_path)
    await init_sqlite()
    db = await get_sqlite()

    await db.execute(
        "INSERT INTO users (email, role, status) VALUES (?, ?, ?)",
        ("u@ex.com", "user", "active"),
    )
    await db.execute(
        "INSERT INTO channel_mappings (user_id, source_chat_id, dest_chat_id, enabled) VALUES (?, ?, ?, ?)",
        (1, 100, 200, 1),
    )
    await db.commit()

    mappings = list(await list_enabled_mappings(db, user_id=1))
    assert len(mappings) == 1
    assert mappings[0].source_chat_id == 100
    assert mappings[0].filters == []


@pytest.mark.asyncio
async def test_list_enabled_mappings_all_four_rule_types(tmp_path):
    db_path = tmp_path / "test.db"
    from app.config import settings

    settings.sqlite_path = str(db_path)
    await init_sqlite()
    db = await get_sqlite()

    await db.execute(
        "INSERT INTO users (email, role, status) VALUES (?, ?, ?)",
        ("u@ex.com", "user", "active"),
    )
    await db.execute(
        "INSERT INTO channel_mappings (user_id, source_chat_id, dest_chat_id, enabled) VALUES (?, ?, ?, ?)",
        (1, 100, 200, 1),
    )
    await db.execute(
        "INSERT INTO mapping_filters (mapping_id, include_text, exclude_text, media_types, regex_pattern) "
        "VALUES (?, ?, ?, ?, ?)",
        (1, "announce", "spam", "text,voice", r"#\d+"),
    )
    await db.commit()

    mappings = list(await list_enabled_mappings(db, user_id=1))
    assert len(mappings) == 1
    assert len(mappings[0].filters) == 1
    f = mappings[0].filters[0]
    assert f.include_text == "announce"
    assert f.exclude_text == "spam"
    assert f.media_types == "text,voice"
    assert f.regex_pattern == r"#\d+"


@pytest.mark.asyncio
async def test_list_enabled_mappings_disabled_excluded(tmp_path):
    db_path = tmp_path / "test.db"
    from app.config import settings

    settings.sqlite_path = str(db_path)
    await init_sqlite()
    db = await get_sqlite()

    await db.execute(
        "INSERT INTO users (email, role, status) VALUES (?, ?, ?)",
        ("u@ex.com", "user", "active"),
    )
    await db.execute(
        "INSERT INTO channel_mappings (user_id, source_chat_id, dest_chat_id, enabled) VALUES (?, ?, ?, ?)",
        (1, 100, 200, 0),
    )
    await db.execute(
        "INSERT INTO mapping_filters (mapping_id, include_text, exclude_text, media_types, regex_pattern) "
        "VALUES (?, ?, ?, ?, ?)",
        (1, "x", None, None, None),
    )
    await db.commit()

    mappings = list(await list_enabled_mappings(db, user_id=1))
    assert len(mappings) == 0


@pytest.mark.asyncio
async def test_list_enabled_mappings_multiple_no_crosstalk(tmp_path):
    db_path = tmp_path / "test.db"
    from app.config import settings

    settings.sqlite_path = str(db_path)
    await init_sqlite()
    db = await get_sqlite()

    await db.execute("INSERT INTO users (email, role, status) VALUES (?, ?, ?)", ("u1@ex.com", "user", "active"))
    await db.execute("INSERT INTO users (email, role, status) VALUES (?, ?, ?)", ("u2@ex.com", "user", "active"))
    await db.execute(
        "INSERT INTO channel_mappings (user_id, source_chat_id, dest_chat_id, enabled) VALUES (?, ?, ?, ?)",
        (1, 10, 20, 1),
    )
    await db.execute(
        "INSERT INTO channel_mappings (user_id, source_chat_id, dest_chat_id, enabled) VALUES (?, ?, ?, ?)",
        (1, 30, 40, 1),
    )
    await db.execute(
        "INSERT INTO mapping_filters (mapping_id, include_text, exclude_text, media_types, regex_pattern) "
        "VALUES (?, ?, ?, ?, ?)",
        (1, "a", None, None, None),
    )
    await db.execute(
        "INSERT INTO mapping_filters (mapping_id, include_text, exclude_text, media_types, regex_pattern) "
        "VALUES (?, ?, ?, ?, ?)",
        (2, "b", None, None, None),
    )
    await db.commit()

    mappings = list(await list_enabled_mappings(db, user_id=1))
    assert len(mappings) == 2
    by_src = {m.source_chat_id: m for m in mappings}
    assert by_src[10].filters[0].include_text == "a"
    assert by_src[30].filters[0].include_text == "b"
