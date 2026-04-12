from __future__ import annotations

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.cleanup import purge_old_login_sessions
from app.db.mongo_indexes import ensure_mongo_indexes
from app.db.sqlite import get_sqlite, init_sqlite
from app.web.routers import (
    accounts,
    accounts_login,
    admin_settings,
    admin_stats,
    admin_users,
    alert_webhooks,
    api_keys,
    auth,
    filters,
    mappings,
    media_assets,
    message_index,
    message_logs,
    schedules,
    stats,
    transforms,
    user_feature_flags,
    worker_logs,
    workers,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_sqlite()
    await purge_old_login_sessions(settings.login_sessions_retention_days)
    if not settings.testing:
        await ensure_mongo_indexes()

    async def _delayed_restore():
        """Restore workers a few seconds after startup so DB, Mongo, etc. are fully ready."""
        await asyncio.sleep(3 if not settings.testing else 0)
        db = await get_sqlite()
        try:
            await workers.restore_workers_from_db(db)
            logger.info("Worker restore completed")
        except Exception as e:
            logger.exception("Worker restore failed: %s", e)
        finally:
            await db.close()

    asyncio.create_task(_delayed_restore())

    alert_task: asyncio.Task | None = None
    if not settings.testing:

        async def _alert_loop() -> None:
            from app.services.alert_checker import check_stale_workers_and_alert

            while True:
                await asyncio.sleep(90)
                db = await get_sqlite()
                try:
                    await check_stale_workers_and_alert(db)
                except Exception as e:
                    logger.warning("alert checker: %s", e)
                finally:
                    await db.close()

        alert_task = asyncio.create_task(_alert_loop())

    yield

    if alert_task is not None:
        alert_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await alert_task
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
    app.include_router(alert_webhooks.router, prefix="/api")
    app.include_router(api_keys.router, prefix="/api")
    app.include_router(user_feature_flags.router, prefix="/api")
    app.include_router(admin_users.router, prefix="/api")
    app.include_router(admin_settings.router, prefix="/api")
    app.include_router(accounts.router, prefix="/api")
    app.include_router(accounts_login.router, prefix="/api")
    app.include_router(mappings.router, prefix="/api")
    app.include_router(schedules.router, prefix="/api")
    app.include_router(filters.router, prefix="/api")
    app.include_router(transforms.router, prefix="/api")
    app.include_router(media_assets.router, prefix="/api")
    app.include_router(message_index.router, prefix="/api")
    app.include_router(message_logs.router, prefix="/api")
    app.include_router(worker_logs.router, prefix="/api")
    app.include_router(workers.router, prefix="/api")
    app.include_router(stats.router, prefix="/api")
    app.include_router(admin_stats.router, prefix="/api")

    return app
