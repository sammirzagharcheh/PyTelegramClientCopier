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
    bot_token: str | None = None
    telegram_test_chat_id: str | None = None
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "telegram_copier"
    sqlite_path: str = "data/app.db"
    sessions_dir: str = "data/sessions"
    log_level: str = "INFO"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    login_sessions_retention_days: int = 7


settings = Settings()

