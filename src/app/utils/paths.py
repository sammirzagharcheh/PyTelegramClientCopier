"""Path utilities shared across the application."""

from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    """Return the project root directory by locating a known marker file.

    Walks up from this file's location until it finds ``pyproject.toml`` or
    ``setup.py``.  Falls back to the repository root heuristic only if no
    marker is found, so the function remains correct even if the package is
    moved within the tree.
    """
    current = Path(__file__).resolve()
    for candidate in (current,) + tuple(current.parents):
        if (candidate / "pyproject.toml").is_file() or (candidate / "setup.py").is_file():
            return candidate
    # Fallback: return the directory containing this file.
    return current.parent


def resolve_asset_path(stored_path: str) -> Path:
    """Resolve a stored media-asset path (relative or absolute) to an absolute Path.

    New assets are stored with paths relative to the project root.  Legacy
    records that contain absolute paths are returned unchanged so that existing
    data continues to work without a data migration.
    """
    p = Path(stored_path)
    if p.is_absolute():
        return p
    return project_root() / p
