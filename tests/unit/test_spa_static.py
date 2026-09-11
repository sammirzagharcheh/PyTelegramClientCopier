"""SPA static serving when FRONTEND_DIST_DIR points at a built frontend."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _make_client(tmp_path, *, with_dist: bool):
    from app.config import settings

    settings.sqlite_path = str(tmp_path / "test.db")
    settings.media_assets_dir = str(tmp_path / "media_assets")
    settings.testing = True

    if with_dist:
        dist = tmp_path / "frontend_dist"
        dist.mkdir()
        (dist / "index.html").write_text(
            "<!doctype html><html><body>spa-root</body></html>",
            encoding="utf-8",
        )
        assets = dist / "assets"
        assets.mkdir()
        (assets / "app.js").write_text("console.log('ok')", encoding="utf-8")
        (dist / "favicon.ico").write_bytes(b"ico")
        settings.frontend_dist_dir = str(dist)
    else:
        settings.frontend_dist_dir = str(tmp_path / "missing-dist")

    from app.web.app import create_app

    return TestClient(create_app())


def test_spa_serves_index_and_fallback(tmp_path):
    with _make_client(tmp_path, with_dist=True) as client:
        root = client.get("/")
        assert root.status_code == 200
        assert "spa-root" in root.text
        assert "text/html" in root.headers.get("content-type", "")

        deep = client.get("/dashboard/mappings")
        assert deep.status_code == 200
        assert "spa-root" in deep.text

        asset = client.get("/assets/app.js")
        assert asset.status_code == 200
        assert "console.log" in asset.text

        favicon = client.get("/favicon.ico")
        assert favicon.status_code == 200

        health = client.get("/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}


def test_spa_missing_dist_still_starts(tmp_path):
    with _make_client(tmp_path, with_dist=False) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}

        missing = client.get("/")
        assert missing.status_code == 404
