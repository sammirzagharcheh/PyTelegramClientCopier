import datetime

import pytest

from app.services.mapping_service import ChannelMapping, MappingFilter, MappingTransform
from app.telegram.handlers import build_message_handler, _save_dest_mapping
from app.db.sqlite import init_sqlite, get_sqlite


class DummySent:
    def __init__(self, msg_id: int):
        self.id = msg_id


class DummyClient:
    def __init__(self):
        self.sent_messages = []
        self.sent_files = []
        self._next_id = 1000

    async def send_message(self, chat_id, text, reply_to=None):
        self.sent_messages.append((chat_id, text, reply_to))
        self._next_id += 1
        return DummySent(self._next_id)

    async def send_file(self, chat_id, media, caption="", reply_to=None):
        self.sent_files.append((chat_id, media, caption, reply_to))
        self._next_id += 1
        return DummySent(self._next_id)


class DummyReply:
    def __init__(self, reply_to_msg_id: int):
        self.reply_to_msg_id = reply_to_msg_id


class DummyMessage:
    def __init__(
        self,
        msg_id: int,
        text: str,
        *,
        media=None,
        photo=False,
        video=False,
        voice=False,
        reply_to_msg_id=None,
    ):
        self.id = msg_id
        self.message = text
        self.text = text
        self.media = media
        self.photo = photo
        self.video = video
        self.voice = voice
        self.date = datetime.datetime.now(datetime.UTC)
        self.reply_to = DummyReply(reply_to_msg_id) if reply_to_msg_id else None


class DummyChat:
    def __init__(self, title: str = "Test Channel"):
        self.title = title


class DummyEvent:
    def __init__(self, chat_id, message, client, chat=None):
        self.chat_id = chat_id
        self.message = message
        self.client = client
        self.chat = chat or DummyChat()


class DummyMongo:
    def __init__(self):
        self.message_logs = self
        self.logs = []

    async def insert_one(self, doc):
        self.logs.append(doc)


class FailingMongo:
    def __init__(self):
        self.message_logs = self

    async def insert_one(self, _doc):
        raise RuntimeError("mongo down")


@pytest.mark.asyncio
async def test_handler_flow_replies_and_media(tmp_path):
    db_path = tmp_path / "test.db"
    from app.config import settings

    settings.sqlite_path = str(db_path)
    await init_sqlite()
    db = await get_sqlite()

    mapping = ChannelMapping(
        id=1,
        user_id=1,
        source_chat_id=10,
        dest_chat_id=20,
        enabled=True,
        filters=[MappingFilter(include_text="hello", exclude_text=None, media_types="text,photo", regex_pattern=None)],
        source_chat_title="Source Channel",
        dest_chat_title="Dest Channel",
    )
    mongo = DummyMongo()
    client = DummyClient()

    # Seed reply mapping for message id 55 -> dest 77
    await _save_dest_mapping(db, user_id=1, source_chat_id=10, source_msg_id=55, dest_chat_id=20, dest_msg_id=77)

    handler = build_message_handler(user_id=1, mappings=[mapping], db=db, mongo_db=mongo)

    # Incoming text message replying to source msg id 55
    event = DummyEvent(
        chat_id=10,
        message=DummyMessage(56, "hello world", reply_to_msg_id=55),
        client=client,
    )
    await handler(event)

    assert len(client.sent_messages) == 1
    assert client.sent_messages[0][2] == 77
    assert mongo.logs[-1]["source_msg_id"] == 56
    assert mongo.logs[-1].get("source_chat_title") == "Test Channel"
    assert mongo.logs[-1].get("dest_chat_title") == "Dest Channel"

    # Incoming photo message (allowed by filter)
    event2 = DummyEvent(
        chat_id=10,
        message=DummyMessage(57, "hello photo", media="photo_bytes", photo=True),
        client=client,
    )
    await handler(event2)

    assert len(client.sent_files) == 1
    assert client.sent_files[0][0] == 20


@pytest.mark.asyncio
async def test_handler_rejected_by_include_text(tmp_path):
    db_path = tmp_path / "test.db"
    from app.config import settings

    settings.sqlite_path = str(db_path)
    await init_sqlite()
    db = await get_sqlite()

    mapping = ChannelMapping(
        id=1,
        user_id=1,
        source_chat_id=10,
        dest_chat_id=20,
        enabled=True,
        filters=[MappingFilter(include_text="required", exclude_text=None, media_types=None, regex_pattern=None)],
        source_chat_title=None,
        dest_chat_title=None,
    )
    mongo = DummyMongo()
    client = DummyClient()
    handler = build_message_handler(user_id=1, mappings=[mapping], db=db, mongo_db=mongo)

    event = DummyEvent(chat_id=10, message=DummyMessage(1, "other text"), client=client)
    await handler(event)

    assert len(client.sent_messages) == 0
    assert len(mongo.logs) == 0


@pytest.mark.asyncio
async def test_handler_rejected_by_exclude_text(tmp_path):
    db_path = tmp_path / "test.db"
    from app.config import settings

    settings.sqlite_path = str(db_path)
    await init_sqlite()
    db = await get_sqlite()

    mapping = ChannelMapping(
        id=1,
        user_id=1,
        source_chat_id=10,
        dest_chat_id=20,
        enabled=True,
        filters=[MappingFilter(include_text=None, exclude_text="spam", media_types=None, regex_pattern=None)],
        source_chat_title=None,
        dest_chat_title=None,
    )
    mongo = DummyMongo()
    client = DummyClient()
    handler = build_message_handler(user_id=1, mappings=[mapping], db=db, mongo_db=mongo)

    event = DummyEvent(chat_id=10, message=DummyMessage(1, "this is spam here"), client=client)
    await handler(event)

    assert len(client.sent_messages) == 0
    assert len(mongo.logs) == 0


@pytest.mark.asyncio
async def test_handler_rejected_by_media_types(tmp_path):
    db_path = tmp_path / "test.db"
    from app.config import settings

    settings.sqlite_path = str(db_path)
    await init_sqlite()
    db = await get_sqlite()

    mapping = ChannelMapping(
        id=1,
        user_id=1,
        source_chat_id=10,
        dest_chat_id=20,
        enabled=True,
        filters=[MappingFilter(include_text=None, exclude_text=None, media_types="text,voice", regex_pattern=None)],
        source_chat_title=None,
        dest_chat_title=None,
    )
    mongo = DummyMongo()
    client = DummyClient()
    handler = build_message_handler(user_id=1, mappings=[mapping], db=db, mongo_db=mongo)

    event = DummyEvent(chat_id=10, message=DummyMessage(1, "photo", photo=True), client=client)
    await handler(event)

    assert len(client.sent_files) == 0
    assert len(mongo.logs) == 0


@pytest.mark.asyncio
async def test_handler_rejected_by_regex(tmp_path):
    db_path = tmp_path / "test.db"
    from app.config import settings

    settings.sqlite_path = str(db_path)
    await init_sqlite()
    db = await get_sqlite()

    mapping = ChannelMapping(
        id=1,
        user_id=1,
        source_chat_id=10,
        dest_chat_id=20,
        enabled=True,
        filters=[MappingFilter(include_text=None, exclude_text=None, media_types=None, regex_pattern=r"#\d+")],
        source_chat_title=None,
        dest_chat_title=None,
    )
    mongo = DummyMongo()
    client = DummyClient()
    handler = build_message_handler(user_id=1, mappings=[mapping], db=db, mongo_db=mongo)

    event = DummyEvent(chat_id=10, message=DummyMessage(1, "order 123"), client=client)
    await handler(event)

    assert len(client.sent_messages) == 0
    assert len(mongo.logs) == 0


@pytest.mark.asyncio
async def test_handler_multiple_filters_second_fails(tmp_path):
    db_path = tmp_path / "test.db"
    from app.config import settings

    settings.sqlite_path = str(db_path)
    await init_sqlite()
    db = await get_sqlite()

    mapping = ChannelMapping(
        id=1,
        user_id=1,
        source_chat_id=10,
        dest_chat_id=20,
        enabled=True,
        filters=[
            MappingFilter(include_text="hello", exclude_text=None, media_types=None, regex_pattern=None),
            MappingFilter(include_text="missing", exclude_text=None, media_types=None, regex_pattern=None),
        ],
        source_chat_title=None,
        dest_chat_title=None,
    )
    mongo = DummyMongo()
    client = DummyClient()
    handler = build_message_handler(user_id=1, mappings=[mapping], db=db, mongo_db=mongo)

    event = DummyEvent(chat_id=10, message=DummyMessage(1, "hello world"), client=client)
    await handler(event)

    assert len(client.sent_messages) == 0
    assert len(mongo.logs) == 0


@pytest.mark.asyncio
async def test_handler_no_filters_all_forwarded(tmp_path):
    db_path = tmp_path / "test.db"
    from app.config import settings

    settings.sqlite_path = str(db_path)
    await init_sqlite()
    db = await get_sqlite()

    mapping = ChannelMapping(
        id=1,
        user_id=1,
        source_chat_id=10,
        dest_chat_id=20,
        enabled=True,
        filters=[],
        source_chat_title=None,
        dest_chat_title=None,
    )
    mongo = DummyMongo()
    client = DummyClient()
    handler = build_message_handler(user_id=1, mappings=[mapping], db=db, mongo_db=mongo)

    event = DummyEvent(chat_id=10, message=DummyMessage(1, "anything goes"), client=client)
    await handler(event)

    assert len(client.sent_messages) == 1
    assert len(mongo.logs) == 1


@pytest.mark.asyncio
async def test_handler_applies_text_regex_and_emoji_transforms(tmp_path):
    db_path = tmp_path / "test.db"
    from app.config import settings

    settings.sqlite_path = str(db_path)
    await init_sqlite()
    db = await get_sqlite()

    mapping = ChannelMapping(
        id=1,
        user_id=1,
        source_chat_id=10,
        dest_chat_id=20,
        enabled=True,
        filters=[],
        source_chat_title=None,
        dest_chat_title=None,
        transforms=[
            MappingTransform(
                id=1,
                rule_type="text",
                find_text="Sam channel",
                replace_text="Tom channel",
                regex_pattern=None,
                regex_flags=None,
                enabled=True,
                priority=10,
            ),
            MappingTransform(
                id=2,
                rule_type="regex",
                find_text=None,
                replace_text="#XXX",
                regex_pattern=r"#\d+",
                regex_flags=None,
                enabled=True,
                priority=20,
            ),
            MappingTransform(
                id=3,
                rule_type="emoji",
                find_text="🔥",
                replace_text="⭐",
                regex_pattern=None,
                regex_flags=None,
                enabled=True,
                priority=30,
            ),
        ],
    )
    mongo = DummyMongo()
    client = DummyClient()
    handler = build_message_handler(user_id=1, mappings=[mapping], db=db, mongo_db=mongo)

    event = DummyEvent(
        chat_id=10,
        message=DummyMessage(1, "Welcome to Sam channel order #123 🔥"),
        client=client,
    )
    await handler(event)

    assert len(client.sent_messages) == 1
    assert client.sent_messages[0][1] == "Welcome to Tom channel order #XXX ⭐"


@pytest.mark.asyncio
async def test_handler_replaces_media_with_uploaded_asset(tmp_path):
    db_path = tmp_path / "test.db"
    from app.config import settings

    settings.sqlite_path = str(db_path)
    await init_sqlite()
    db = await get_sqlite()

    replacement_asset = tmp_path / "replacement.jpg"
    replacement_asset.write_bytes(b"fake-jpg-bytes")

    mapping = ChannelMapping(
        id=1,
        user_id=1,
        source_chat_id=10,
        dest_chat_id=20,
        enabled=True,
        filters=[],
        source_chat_title=None,
        dest_chat_title=None,
        transforms=[
            MappingTransform(
                id=1,
                rule_type="media",
                replacement_media_asset_id=1,
                replacement_media_asset_path=str(replacement_asset),
                apply_to_media_types="photo",
                enabled=True,
                priority=1,
            )
        ],
    )
    mongo = DummyMongo()
    client = DummyClient()
    handler = build_message_handler(user_id=1, mappings=[mapping], db=db, mongo_db=mongo)

    event = DummyEvent(
        chat_id=10,
        message=DummyMessage(1, "caption", media="source-media", photo=True),
        client=client,
    )
    await handler(event)

    assert len(client.sent_files) == 1
    # send_file should use replacement asset path, not original source media payload
    assert client.sent_files[0][1] == str(replacement_asset)
    assert client.sent_files[0][2] == "caption"


@pytest.mark.asyncio
async def test_handler_applies_template_transform(tmp_path):
    db_path = tmp_path / "test.db"
    from app.config import settings

    settings.sqlite_path = str(db_path)
    await init_sqlite()
    db = await get_sqlite()

    mapping = ChannelMapping(
        id=1,
        user_id=1,
        source_chat_id=10,
        dest_chat_id=20,
        enabled=True,
        filters=[],
        source_chat_title="Source A",
        dest_chat_title="Dest B",
        transforms=[
            MappingTransform(
                id=1,
                rule_type="text",
                find_text="Sam",
                replace_text="Tom",
                enabled=True,
                priority=10,
            ),
            MappingTransform(
                id=2,
                rule_type="template",
                replace_text="[{{source_chat_title}}] {{text}} (#{{message_id}})",
                apply_to_media_types="text",
                enabled=True,
                priority=20,
            ),
        ],
    )
    mongo = DummyMongo()
    client = DummyClient()
    handler = build_message_handler(user_id=1, mappings=[mapping], db=db, mongo_db=mongo)

    event = DummyEvent(
        chat_id=10,
        message=DummyMessage(42, "hello Sam"),
        client=client,
        chat=DummyChat("Channel A"),
    )
    await handler(event)

    assert len(client.sent_messages) == 1
    assert client.sent_messages[0][1] == "[Channel A] hello Tom (#42)"


@pytest.mark.asyncio
async def test_handler_matches_alternate_source_chat_id_formats(tmp_path):
    db_path = tmp_path / "test.db"
    from app.config import settings

    settings.sqlite_path = str(db_path)
    await init_sqlite()
    db = await get_sqlite()

    source_full = -1001234567890
    source_legacy = source_full + 1000000000000

    mapping = ChannelMapping(
        id=1,
        user_id=1,
        source_chat_id=source_full,
        dest_chat_id=20,
        enabled=True,
        filters=[],
        source_chat_title=None,
        dest_chat_title=None,
    )
    mongo = DummyMongo()
    client = DummyClient()
    handler = build_message_handler(user_id=1, mappings=[mapping], db=db, mongo_db=mongo)

    # Incoming event uses legacy format, mapping uses full format.
    event = DummyEvent(
        chat_id=source_legacy,
        message=DummyMessage(5, "compat message"),
        client=client,
    )
    await handler(event)

    assert len(client.sent_messages) == 1
    assert client.sent_messages[0][0] == 20
    assert client.sent_messages[0][1] == "compat message"


@pytest.mark.asyncio
async def test_handler_forwards_even_if_mongo_log_write_fails(tmp_path):
    db_path = tmp_path / "test.db"
    from app.config import settings

    settings.sqlite_path = str(db_path)
    await init_sqlite()
    db = await get_sqlite()

    mapping = ChannelMapping(
        id=1,
        user_id=1,
        source_chat_id=10,
        dest_chat_id=20,
        enabled=True,
        filters=[],
        source_chat_title=None,
        dest_chat_title=None,
    )
    mongo = FailingMongo()
    client = DummyClient()
    handler = build_message_handler(user_id=1, mappings=[mapping], db=db, mongo_db=mongo)

    event = DummyEvent(chat_id=10, message=DummyMessage(9, "hello"), client=client)
    await handler(event)

    assert len(client.sent_messages) == 1
    assert client.sent_messages[0][1] == "hello"

