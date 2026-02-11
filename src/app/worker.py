from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path

from app.config import settings
from app.db.mongo import get_mongo_db
from app.db.sqlite import get_sqlite, init_sqlite
from app.services.mapping_service import list_enabled_mappings
from app.telegram.client_manager import attach_handler, start_user_client
from app.telegram.handlers import build_message_handler

logger = logging.getLogger(__name__)


def _worker_session_path(session_path: str) -> str:
    """Use a copy of the session to avoid 'database is locked' when another
    process or file sync holds the original. Returns path to worker's session copy.
    Falls back to original path if copy fails (e.g. source locked for read).
    """
    base = Path(__file__).resolve().parents[2]
    path = (base / session_path).resolve() if not Path(session_path).is_absolute() else Path(session_path).resolve()
    worker_path = path.parent / f"{path.stem}_worker.session"
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
    handler = build_message_handler(user_id=user_id, mappings=mappings, db=db, mongo_db=mongo_db)
    attach_handler(client, handler)

    await client.run_until_disconnected()


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

