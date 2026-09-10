"""MongoDB client - uses app_settings (SQLite) if set, else env vars."""

from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.services.app_settings import get_setting_sync


def _resolve_mongo_uri() -> str:
    stored = get_setting_sync("mongo_uri")
    return stored if stored else settings.mongo_uri


def _resolve_mongo_db() -> str:
    stored = get_setting_sync("mongo_db")
    return stored if stored else settings.mongo_db


def get_mongo_client() -> AsyncIOMotorClient:
    kwargs: dict = {}
    if settings.testing:
        # Fail fast in CI/tests when Mongo is not running.
        kwargs["serverSelectionTimeoutMS"] = 500
        kwargs["connectTimeoutMS"] = 500
    return AsyncIOMotorClient(_resolve_mongo_uri(), **kwargs)


def get_mongo_db():
    client = get_mongo_client()
    return client[_resolve_mongo_db()]
