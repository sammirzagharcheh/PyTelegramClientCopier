from __future__ import annotations

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db.cleanup import purge_old_login_sessions
from app.db.mongo_indexes import ensure_mongo_indexes
from app.db.sqlite import get_sqlite, init_sqlite
from app.web.routers import (
    accounts,
    accounts_login,
    admin_invites,
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
    webhook_logs,
    worker_logs,
    workers,
)

logger = logging.getLogger(__name__)


def _mount_spa(app: FastAPI) -> None:
    """Serve the Vite build when FRONTEND_DIST_DIR points at a valid dist folder."""
    raw = (settings.frontend_dist_dir or "").strip()
    if not raw:
        return
    dist = Path(raw)
    index = dist / "index.html"
    if not dist.is_dir() or not index.is_file():
        logger.info("SPA dist not found at %s; API-only mode", dist)
        return

    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="frontend-assets")

    @app.get("/")
    async def spa_root():
        return FileResponse(index)

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        candidate = (dist / full_path).resolve()
        try:
            candidate.relative_to(dist.resolve())
        except ValueError:
            return FileResponse(index)
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)

    logger.info("Serving SPA from %s", dist)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_sqlite()
    await purge_old_login_sessions(settings.login_sessions_retention_days)
    if not settings.testing:
        await ensure_mongo_indexes()

    restore_task: asyncio.Task | None = None
    if not settings.testing:

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

        restore_task = asyncio.create_task(_delayed_restore())

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

    if restore_task is not None:
        restore_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await restore_task
    if alert_task is not None:
        alert_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await alert_task
    if not settings.testing:
        db = await get_sqlite()
        try:
            await workers.terminate_all_workers(db)
        finally:
            await db.close()


def create_app() -> FastAPI:
    app = FastAPI(title="Telegram Client Copier", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost",
            "http://127.0.0.1",
            "http://localhost:5173",
            "http://localhost:3000",
        ],
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
    app.include_router(admin_invites.router, prefix="/api")
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
    app.include_router(webhook_logs.router, prefix="/api")
    app.include_router(workers.router, prefix="/api")
    app.include_router(stats.router, prefix="/api")
    app.include_router(admin_stats.router, prefix="/api")

    # Mount SPA last so /api and /health take precedence over the catch-all.
    _mount_spa(app)

    return app
