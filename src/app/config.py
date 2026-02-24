from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def project_root() -> Path:
    """Return the project root by searching for a pyproject.toml or setup.py marker.

    Walks up from this file's location so the result is correct regardless of the
    current working directory, and avoids hard-coding a fixed number of parent
    directories that would break if the file is moved.
    """
    current = Path(__file__).resolve()
    for candidate in (current,) + tuple(current.parents):
        if (candidate / "pyproject.toml").is_file() or (candidate / "setup.py").is_file():
            return candidate
    return current.parent


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
    media_assets_dir: str = "data/media_assets"
    log_level: str = "INFO"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    login_sessions_retention_days: int = 7


settings = Settings()

