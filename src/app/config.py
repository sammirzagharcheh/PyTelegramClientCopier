from __future__ import annotations

from pydantic import model_validator
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
    db_backend: str = "postgres"  # postgres | sqlite (sqlite kept for rollback/tests)
    database_url: str | None = None
    sqlite_path: str = "data/app.db"
    sessions_dir: str = "data/sessions"
    media_assets_dir: str = "data/media_assets"
    media_upload_max_bytes: int = 52_428_800  # 50 MiB
    log_level: str = "INFO"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    login_sessions_retention_days: int = 7
    testing: bool = False  # TESTING=1 skips slow startup (Mongo indexes, worker restore delay)

    @model_validator(mode="after")
    def _validate_database_backend(self) -> "Settings":
        backend = (self.db_backend or "").strip().lower()
        if backend not in {"sqlite", "postgres"}:
            raise ValueError("DB_BACKEND must be either 'sqlite' or 'postgres'")
        self.db_backend = backend
        if backend == "postgres" and not self.database_url:
            raise ValueError("DATABASE_URL is required when DB_BACKEND=postgres")
        return self


settings = Settings()

