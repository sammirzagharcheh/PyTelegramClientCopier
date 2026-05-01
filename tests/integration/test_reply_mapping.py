import pytest

from app.db.gateway import get_db_connection, init_db
from app.telegram.handlers import _lookup_reply_dest_id, _save_dest_mapping


@pytest.mark.asyncio
async def test_reply_mapping_lookup_and_save(tmp_path):
    await init_db()
    db = await get_db_connection()
    await _save_dest_mapping(
        db=db,
        user_id=1,
        source_chat_id=100,
        source_msg_id=200,
        dest_chat_id=300,
        dest_msg_id=400,
    )

    dest_id = await _lookup_reply_dest_id(
        db=db,
        user_id=1,
        source_chat_id=100,
        source_reply_msg_id=200,
        dest_chat_id=300,
    )
    assert dest_id == 400

