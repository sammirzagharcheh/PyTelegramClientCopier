from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    api_id: int | None = None
    api_hash: str | None = None
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "telegram_copier"
    sqlite_path: str = "data/app.db"
    log_level: str = "INFO"


settings = Settings()

