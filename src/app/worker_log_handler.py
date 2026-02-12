"""MongoDB logging handler for worker processes."""

from __future__ import annotations

import logging
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
    """Logging handler that writes worker logs to MongoDB worker_logs collection."""

    def __init__(self, user_id: int, account_id: int | None = None):
        super().__init__()
        self._user_id = user_id
        self._account_id = account_id

    def emit(self, record: logging.LogRecord) -> None:
        try:
            from pymongo import MongoClient

            uri = _resolve_mongo_uri()
            db_name = _resolve_mongo_db()
            client = MongoClient(uri)
            db = client[db_name]
            doc: dict[str, Any] = {
                "user_id": self._user_id,
                "account_id": self._account_id,
                "level": record.levelname,
                "message": self.format(record),
                "timestamp": datetime.now(timezone.utc),
            }
            db.worker_logs.insert_one(doc)
            client.close()
        except Exception:
            pass  # Graceful no-op if MongoDB unavailable
