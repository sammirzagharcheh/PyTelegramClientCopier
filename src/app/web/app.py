from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.cleanup import purge_old_login_sessions
from app.db.sqlite import get_sqlite, init_sqlite
from app.web.routers import (
    accounts,
    accounts_login,
    admin_settings,
    admin_users,
    auth,
    filters,
    mappings,
    message_index,
    message_logs,
    worker_logs,
    workers,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_sqlite()
    await purge_old_login_sessions(settings.login_sessions_retention_days)

    async def _delayed_restore():
        """Restore workers a few seconds after startup so DB, Mongo, etc. are fully ready."""
        await asyncio.sleep(3)
        db = await get_sqlite()
        try:
            await workers.restore_workers_from_db(db)
            logger.info("Worker restore completed")
        except Exception as e:
            logger.exception("Worker restore failed: %s", e)
        finally:
            await db.close()

    asyncio.create_task(_delayed_restore())
    yield
    db = await get_sqlite()
    try:
        await workers.terminate_all_workers(db)
    finally:
        await db.close()


def create_app() -> FastAPI:
    app = FastAPI(title="Telegram Client Copier", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    app.include_router(auth.router, prefix="/api")
    app.include_router(admin_users.router, prefix="/api")
    app.include_router(admin_settings.router, prefix="/api")
    app.include_router(accounts.router, prefix="/api")
    app.include_router(accounts_login.router, prefix="/api")
    app.include_router(mappings.router, prefix="/api")
    app.include_router(filters.router, prefix="/api")
    app.include_router(message_index.router, prefix="/api")
    app.include_router(message_logs.router, prefix="/api")
    app.include_router(worker_logs.router, prefix="/api")
    app.include_router(workers.router, prefix="/api")

    return app
