"""Lifespan behavior under TESTING=1 (no background worker restore)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


def test_testing_lifespan_skips_worker_restore(tmp_path):
    from app.config import settings

    settings.sqlite_path = str(tmp_path / "test.db")
    settings.media_assets_dir = str(tmp_path / "media_assets")
    settings.testing = True

    with patch("app.web.app.workers.restore_workers_from_db", new_callable=AsyncMock) as restore:
        with patch("app.web.app.workers.terminate_all_workers", new_callable=AsyncMock) as terminate:
            from app.web.app import create_app

            app = create_app()
            with TestClient(app) as client:
                assert client.get("/health").status_code == 200

    restore.assert_not_called()
    terminate.assert_not_called()
