"""Tests for VPS backup + prune scripts (requires bash)."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKUP_SCRIPT = REPO_ROOT / "scripts" / "backup-vps-data.sh"
PRUNE_SCRIPT = REPO_ROOT / "scripts" / "prune-vps-backups.sh"


def _bash() -> str:
    candidates: list[str] = []
    git = shutil.which("git")
    if git:
        git_bash = Path(git).resolve().parent.parent / "bin" / "bash.exe"
        if git_bash.is_file():
            candidates.append(str(git_bash))
    for name in ("bash", "bash.exe"):
        found = shutil.which(name)
        if found and found not in candidates:
            lower = found.lower().replace("/", "\\")
            if lower.endswith("system32\\bash.exe"):
                continue
            candidates.append(found)
    if not candidates:
        found = shutil.which("bash")
        if found:
            candidates.append(found)
    if not candidates:
        pytest.skip("bash is required to test VPS backup/prune scripts")
    return candidates[0]


def _to_bash_path(path: Path, bash: str) -> str:
    resolved = str(path.resolve())
    bash_l = bash.replace("\\", "/").lower()
    if "system32/bash" in bash_l or "windowsapps" in bash_l:
        if len(resolved) >= 2 and resolved[1] == ":":
            drive = resolved[0].lower()
            rest = resolved[2:].replace("\\", "/")
            return f"/mnt/{drive}{rest}"
    return resolved.replace("\\", "/")


def _run_script(
    script: Path,
    env: dict[str, str],
    *,
    check: bool = True,
    clear_keys: tuple[str, ...] = ("BACKUP_KEEP", "BACKUP_DIR", "BACKUP_CONF", "DRY_RUN"),
) -> subprocess.CompletedProcess[str]:
    bash = _bash()
    script_path = _to_bash_path(script, bash)
    merged = {**os.environ}
    for key in clear_keys:
        merged.pop(key, None)
    for k, v in env.items():
        if k.endswith("_DIR") or k in {"INSTALL_DIR", "BACKUP_CONF"}:
            merged[k] = _to_bash_path(Path(v), bash)
        else:
            merged[k] = v
    return subprocess.run(
        [bash, script_path],
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


def _seed_snapshots(backups: Path, count: int) -> list[Path]:
    backups.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for i in range(count):
        # Distinct mtimes so ls -t ordering is stable.
        snap = backups / f"pre-update-20260101-1200{i:02d}-{i}"
        snap.mkdir()
        (snap / "marker.txt").write_text(str(i), encoding="utf-8")
        os.utime(snap, (1_700_000_000 + i, 1_700_000_000 + i))
        created.append(snap)
        time.sleep(0.01)
    return created


def test_backup_creates_snapshot_with_sqlite_sessions_env(tmp_path: Path) -> None:
    install = tmp_path / "opt"
    install.mkdir()
    _seed_install(install)
    backups = tmp_path / "backups"

    result = _run_script(
        BACKUP_SCRIPT,
        {
            "INSTALL_DIR": str(install),
            "BACKUP_DIR": str(backups),
            "BACKUP_KEEP": "5",
        },
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

    result = _run_script(
        BACKUP_SCRIPT,
        {
            "INSTALL_DIR": str(install),
            "BACKUP_DIR": str(backups),
            "SKIP_BACKUP": "1",
        },
    )
    assert result.returncode == 0
    assert not backups.exists() or list(backups.glob("pre-update-*")) == []


def test_backup_prune_keeps_only_n_backups(tmp_path: Path) -> None:
    install = tmp_path / "opt"
    install.mkdir()
    _seed_install(install)
    backups = tmp_path / "backups"

    for _ in range(4):
        _run_script(
            BACKUP_SCRIPT,
            {
                "INSTALL_DIR": str(install),
                "BACKUP_DIR": str(backups),
                "BACKUP_KEEP": "2",
            },
        )

    snaps = sorted(backups.glob("pre-update-*"))
    assert len(snaps) == 2


def test_prune_default_keeps_10(tmp_path: Path) -> None:
    install = tmp_path / "opt"
    install.mkdir()
    backups = install / "backups"
    _seed_snapshots(backups, 12)

    result = _run_script(
        PRUNE_SCRIPT,
        {"INSTALL_DIR": str(install)},
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert len(list(backups.glob("pre-update-*"))) == 10


def test_prune_reads_backup_conf(tmp_path: Path) -> None:
    install = tmp_path / "opt"
    install.mkdir()
    backups = install / "backups"
    _seed_snapshots(backups, 6)
    (install / "backup.conf").write_text("BACKUP_KEEP=3\n", encoding="utf-8")

    result = _run_script(PRUNE_SCRIPT, {"INSTALL_DIR": str(install)})
    assert result.returncode == 0, result.stderr + result.stdout
    assert len(list(backups.glob("pre-update-*"))) == 3


def test_prune_env_overrides_backup_conf(tmp_path: Path) -> None:
    install = tmp_path / "opt"
    install.mkdir()
    backups = install / "backups"
    _seed_snapshots(backups, 6)
    (install / "backup.conf").write_text("BACKUP_KEEP=2\n", encoding="utf-8")

    result = _run_script(
        PRUNE_SCRIPT,
        {"INSTALL_DIR": str(install), "BACKUP_KEEP": "4"},
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert len(list(backups.glob("pre-update-*"))) == 4


def test_prune_dry_run_does_not_delete(tmp_path: Path) -> None:
    install = tmp_path / "opt"
    install.mkdir()
    backups = install / "backups"
    _seed_snapshots(backups, 5)
    (install / "backup.conf").write_text("BACKUP_KEEP=2\n", encoding="utf-8")

    result = _run_script(
        PRUNE_SCRIPT,
        {"INSTALL_DIR": str(install), "DRY_RUN": "1"},
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "DRY_RUN would prune" in result.stdout
    assert len(list(backups.glob("pre-update-*"))) == 5


@pytest.mark.parametrize("bad", ["0", "abc", "-1", ""])
def test_prune_rejects_invalid_keep(tmp_path: Path, bad: str) -> None:
    install = tmp_path / "opt"
    install.mkdir()
    backups = install / "backups"
    _seed_snapshots(backups, 3)

    result = _run_script(
        PRUNE_SCRIPT,
        {"INSTALL_DIR": str(install), "BACKUP_KEEP": bad},
        check=False,
    )
    assert result.returncode != 0
    assert len(list(backups.glob("pre-update-*"))) == 3
