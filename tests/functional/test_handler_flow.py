import datetime

import pytest

from app.services.mapping_service import ChannelMapping, MappingFilter
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

