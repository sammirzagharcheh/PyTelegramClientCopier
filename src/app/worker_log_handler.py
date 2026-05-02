"""MongoDB logging handler for worker processes."""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.services.app_settings import get_setting_sync


def _resolve_mongo_uri() -> str:
    stored = get_setting_sync("mongo_uri")
    return stored if stored else settings.mongo_uri


def _resolve_mongo_db() -> str:
    stored = get_setting_sync("mongo_db")
    return stored if stored else settings.mongo_db


class MongoWorkerLogHandler(logging.Handler):
    """Logging handler that writes worker logs to MongoDB worker_logs collection.

    Inserts run in the default asyncio executor when a loop is running so Mongo I/O does not
    block Telethon coroutines (blocking here can stall update handling and drop forwards).
    """

    def __init__(self, user_id: int, account_id: int | None = None):
        super().__init__()
        self._user_id = user_id
        self._account_id = account_id

    def emit(self, record: logging.LogRecord) -> None:
        try:
            formatted = self.format(record)
        except Exception:
            return

        uid = self._user_id
        aid = self._account_id
        level = record.levelname
        ts = datetime.now(timezone.utc)

        def _sync_insert() -> None:
            try:
                from pymongo import MongoClient

                uri = _resolve_mongo_uri()
                db_name = _resolve_mongo_db()
                client = MongoClient(uri, serverSelectionTimeoutMS=8000)
                try:
                    db = client[db_name]
                    doc: dict[str, Any] = {
                        "user_id": uid,
                        "account_id": aid,
                        "level": level,
                        "message": formatted,
                        "timestamp": ts,
                    }
                    db.worker_logs.insert_one(doc)
                finally:
                    client.close()
            except Exception as e:
                print(
                    f"[MongoWorkerLogHandler] Failed to write log to MongoDB: {e}",
                    file=sys.stderr,
                )

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            _sync_insert()
            return
        loop.run_in_executor(None, _sync_insert)


def test_mongo_connection() -> tuple[str | None, str]:
    """Test MongoDB write. Returns (error_message, db_name). error_message is None on success."""
    try:
        from pymongo import MongoClient

        uri = _resolve_mongo_uri()
        db_name = _resolve_mongo_db()
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        db = client[db_name]
        doc = {"_test": True, "source": "worker_log_handler"}
        db.worker_logs.insert_one(doc)
        db.worker_logs.delete_one({"_test": True})
        client.close()
        return (None, db_name)
    except Exception as e:
        return (str(e), _resolve_mongo_db())
