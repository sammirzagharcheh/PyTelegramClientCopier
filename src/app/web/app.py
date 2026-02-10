from __future__ import annotations

from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Telegram Client Copier")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app

