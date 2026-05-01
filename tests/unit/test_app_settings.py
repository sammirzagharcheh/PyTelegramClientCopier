"""Unit tests for app_settings in postgres-only runtime."""

from app.services.app_settings import get_setting_sync


def test_get_setting_sync_returns_none_in_postgres_only_runtime():
    """Sync helper always falls back to env in postgres-only mode."""
    assert get_setting_sync("mongo_db") is None
