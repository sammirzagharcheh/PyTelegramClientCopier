"""Dev Docker overlay must load bind-mounted src over the image wheel."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_docker_dev_overlay_sets_pythonpath_to_src():
    text = (ROOT / "docker-compose.dev.yml").read_text(encoding="utf-8")
    assert "PYTHONPATH: /app/src" in text
