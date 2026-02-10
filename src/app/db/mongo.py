from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings


def get_mongo_client() -> AsyncIOMotorClient:
    return AsyncIOMotorClient(settings.mongo_uri)


def get_mongo_db():
    client = get_mongo_client()
    return client[settings.mongo_db]

