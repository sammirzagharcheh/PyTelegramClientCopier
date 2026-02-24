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


@pytest.mark.asyncio
async def test_list_enabled_mappings_loads_transforms(tmp_path):
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
        "INSERT INTO mapping_transform_rules "
        "(mapping_id, rule_type, find_text, replace_text, enabled, priority) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (1, "text", "Sam channel", "Tom channel", 1, 20),
    )
    await db.execute(
        "INSERT INTO mapping_transform_rules "
        "(mapping_id, rule_type, regex_pattern, replace_text, regex_flags, enabled, priority) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (1, "regex", r"#\d+", "#XXX", "i", 1, 10),
    )
    await db.commit()

    mappings = list(await list_enabled_mappings(db, user_id=1))
    assert len(mappings) == 1
    transforms = mappings[0].transforms
    assert len(transforms) == 2
    assert transforms[0].rule_type == "regex"
    assert transforms[0].regex_pattern == r"#\d+"
    assert transforms[0].regex_flags == "i"
    assert transforms[1].rule_type == "text"
    assert transforms[1].find_text == "Sam channel"
    assert transforms[1].replace_text == "Tom channel"


@pytest.mark.asyncio
async def test_list_enabled_mappings_loads_media_transform_asset_path(tmp_path):
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
        "INSERT INTO media_assets (user_id, name, file_path, media_kind) VALUES (?, ?, ?, ?)",
        (1, "photo", "/tmp/replacement.jpg", "photo"),
    )
    await db.execute(
        "INSERT INTO mapping_transform_rules "
        "(mapping_id, rule_type, replacement_media_asset_id, apply_to_media_types, enabled, priority) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (1, "media", 1, "photo", 1, 5),
    )
    await db.commit()

    mappings = list(await list_enabled_mappings(db, user_id=1))
    assert len(mappings) == 1
    transforms = mappings[0].transforms
    assert len(transforms) == 1
    assert transforms[0].rule_type == "media"
    assert transforms[0].replacement_media_asset_id == 1
    assert transforms[0].replacement_media_asset_path == "/tmp/replacement.jpg"
    assert transforms[0].apply_to_media_types == "photo"
