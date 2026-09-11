"""Tests for scripts/backup-vps-data.sh (requires bash)."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "backup-vps-data.sh"


def _bash() -> str:
    # Prefer Git Bash on Windows; system32\\bash.EXE is often WSL and cannot see D:\\ paths.
    candidates: list[str] = []
    git = shutil.which("git")
    if git:
        git_bash = Path(git).resolve().parent.parent / "bin" / "bash.exe"
        if git_bash.is_file():
            candidates.append(str(git_bash))
    for name in ("bash", "bash.exe"):
        found = shutil.which(name)
        if found and found not in candidates:
            # Skip WSL launcher when Git Bash is available.
            lower = found.lower().replace("/", "\\")
            if lower.endswith("system32\\bash.exe"):
                continue
            candidates.append(found)
    if not candidates:
        found = shutil.which("bash")
        if found:
            candidates.append(found)
    if not candidates:
        pytest.skip("bash is required to test backup-vps-data.sh")
    return candidates[0]


def _to_bash_path(path: Path, bash: str) -> str:
    """Convert a Windows path for the bash that will run the script."""
    resolved = str(path.resolve())
    bash_l = bash.replace("\\", "/").lower()
    if "system32/bash" in bash_l or "windowsapps" in bash_l:
        # WSL: D:\\foo -> /mnt/d/foo
        if len(resolved) >= 2 and resolved[1] == ":":
            drive = resolved[0].lower()
            rest = resolved[2:].replace("\\", "/")
            return f"/mnt/{drive}{rest}"
    return resolved.replace("\\", "/")


def _run_backup(env: dict[str, str], check: bool = True) -> subprocess.CompletedProcess[str]:
    bash = _bash()
    script = _to_bash_path(SCRIPT, bash)
    converted: dict[str, str] = {}
    for k, v in env.items():
        if k.endswith("_DIR") or k == "INSTALL_DIR":
            converted[k] = _to_bash_path(Path(v), bash)
        else:
            converted[k] = v
    merged = {**os.environ, **converted}
    return subprocess.run(
        [bash, script],
        env=merged,
        capture_output=True,
        text=True,
        check=check,
    )


def _seed_install(root: Path) -> None:
    data = root / "data"
    (data / "sessions").mkdir(parents=True)
    (data / "media_assets").mkdir(parents=True)
    (data / "app.db").write_bytes(b"sqlite-bytes")
    (data / "sessions" / "acct.session").write_text("session", encoding="utf-8")
    (data / "media_assets" / "x.bin").write_bytes(b"media")
    (root / ".env").write_text(
        "SQLITE_PATH=data/app.db\n"
        "SESSIONS_DIR=data/sessions\n"
        "MEDIA_ASSETS_DIR=data/media_assets\n"
        "JWT_SECRET=test-secret\n",
        encoding="utf-8",
    )


def test_backup_creates_snapshot_with_sqlite_sessions_env(tmp_path: Path) -> None:
    install = tmp_path / "opt"
    install.mkdir()
    _seed_install(install)
    backups = tmp_path / "backups"

    result = _run_backup(
        {
            "INSTALL_DIR": str(install),
            "BACKUP_DIR": str(backups),
            "BACKUP_KEEP": "5",
        }
    )
    assert result.returncode == 0, result.stderr + result.stdout

    snaps = sorted(backups.glob("pre-update-*"))
    assert len(snaps) == 1
    snap = snaps[0]
    assert (snap / "sqlite" / "app.db").read_bytes() == b"sqlite-bytes"
    assert (snap / "sessions" / "acct.session").read_text(encoding="utf-8") == "session"
    assert (snap / "media_assets" / "x.bin").read_bytes() == b"media"
    assert (snap / "dotenv.env").read_text(encoding="utf-8").find("JWT_SECRET=test-secret") >= 0
    assert (snap / "data_tree" / "app.db").is_file()


def test_skip_backup_is_noop(tmp_path: Path) -> None:
    install = tmp_path / "opt"
    install.mkdir()
    _seed_install(install)
    backups = tmp_path / "backups"

    result = _run_backup(
        {
            "INSTALL_DIR": str(install),
            "BACKUP_DIR": str(backups),
            "SKIP_BACKUP": "1",
        }
    )
    assert result.returncode == 0
    assert not backups.exists() or list(backups.glob("pre-update-*")) == []


def test_prune_keeps_only_n_backups(tmp_path: Path) -> None:
    install = tmp_path / "opt"
    install.mkdir()
    _seed_install(install)
    backups = tmp_path / "backups"

    for _ in range(4):
        _run_backup(
            {
                "INSTALL_DIR": str(install),
                "BACKUP_DIR": str(backups),
                "BACKUP_KEEP": "2",
            }
        )

    snaps = sorted(backups.glob("pre-update-*"))
    assert len(snaps) == 2
