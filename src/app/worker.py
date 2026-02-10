from __future__ import annotations

import asyncio

from app.db.mongo import get_mongo_db
from app.db.sqlite import get_sqlite, init_sqlite
from app.services.mapping_service import list_enabled_mappings
from app.telegram.client_manager import attach_handler, start_user_client
from app.telegram.handlers import build_message_handler


async def run_worker(user_id: int, session_path: str) -> None:
    await init_sqlite()
    mongo_db = get_mongo_db()
    db = await get_sqlite()
    mappings = list(await list_enabled_mappings(db, user_id))

    client = await start_user_client(session_path)
    handler = build_message_handler(user_id=user_id, mappings=mappings, db=db, mongo_db=mongo_db)
    attach_handler(client, handler)

    await client.run_until_disconnected()


def run_worker_sync(user_id: int, session_path: str) -> None:
    asyncio.run(run_worker(user_id, session_path))

