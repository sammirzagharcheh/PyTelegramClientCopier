from __future__ import annotations

import asyncio
import logging
import os
import shutil
from pathlib import Path

from app.config import settings
from app.db.mongo import get_mongo_db
from app.db.sqlite import get_sqlite, init_sqlite
from app.services.mapping_service import list_enabled_mappings
from app.worker_log_handler import MongoWorkerLogHandler, test_mongo_connection
from app.telegram.client_manager import attach_handler, start_user_client
from app.telegram.handlers import build_message_handler

logger = logging.getLogger(__name__)


def _worker_session_path(session_path: str) -> str:
    """Use a unique copy of the session per worker process to avoid 'database is locked'
    when another worker or file sync holds a shared copy. Returns path to worker's session copy.
    Falls back to original path if copy fails (e.g. source locked for read).
    """
    base = Path(__file__).resolve().parents[2]
    path = (base / session_path).resolve() if not Path(session_path).is_absolute() else Path(session_path).resolve()
    pid = os.getpid()
    worker_path = path.parent / f"{path.stem}_worker_{pid}.session"
    try:
        shutil.copy2(path, worker_path)
        return str(worker_path)
    except OSError as e:
        logger.warning("Could not copy session to worker path (%s), using original: %s", e, path)
        return str(path)


async def run_worker(
    user_id: int,
    session_path: str,
    telegram_account_id: int | None = None,
) -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    fmt = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    logging.basicConfig(level=level, format=fmt)
    # Also log to file so UI-started workers produce visible logs
    try:
        log_path = Path(__file__).resolve().parents[2] / "data" / "worker.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(logging.Formatter(fmt))
        logging.getLogger().addHandler(fh)
    except Exception:
        pass  # non-fatal

    try:
        mongo_handler = MongoWorkerLogHandler(user_id=user_id, account_id=telegram_account_id)
        mongo_handler.setLevel(level)
        mongo_handler.setFormatter(logging.Formatter("%(message)s"))
        logging.getLogger().addHandler(mongo_handler)
        # Test MongoDB connectivity; log result so user sees it in worker.log
        err, db_name = test_mongo_connection()
        if err:
            logger.warning("MongoDB worker_logs disabled (connection failed): %s", err)
        else:
            logger.info("MongoDB worker_logs connected OK (database: %s)", db_name)
    except Exception as e:
        logger.warning("MongoDB worker_logs handler skipped: %s", e)

    try:
        await init_sqlite()
        mongo_db = get_mongo_db()
        db = await get_sqlite()
        mappings = list(
            await list_enabled_mappings(db, user_id, telegram_account_id=telegram_account_id)
        )

        source_ids = sorted({m.source_chat_id for m in mappings})
        logger.info(
            "Worker starting: user_id=%s account_id=%s mappings=%d source_chat_ids=%s",
            user_id, telegram_account_id, len(mappings), source_ids,
        )
        if not mappings:
            logger.warning("No mappings loaded - worker will not forward any messages")

        worker_session = _worker_session_path(session_path)
        logger.debug("Using worker session copy: %s", worker_session)
        client = await start_user_client(worker_session)
        logger.info("Connected to Telegram: user_id=%s account_id=%s", user_id, telegram_account_id)
        handler = build_message_handler(user_id=user_id, mappings=mappings, db=db, mongo_db=mongo_db)
        attach_handler(client, handler)

        await client.run_until_disconnected()
        logger.info("Worker disconnected: user_id=%s account_id=%s (Telegram client closed)", user_id, telegram_account_id)
    except Exception as e:
        logger.exception(
            "Worker exited with uncaught exception: user_id=%s account_id=%s: %s",
            user_id, telegram_account_id, e,
        )
        raise


def run_worker_sync(
    user_id: int,
    session_path: str,
    telegram_account_id: int | None = None,
) -> None:
    asyncio.run(
        run_worker(
            user_id=user_id,
            session_path=session_path,
            telegram_account_id=telegram_account_id,
        )
    )

