"""Registry path helpers for user vs bot workers."""

from __future__ import annotations

from pathlib import Path

BOT_REGISTRY_PREFIX = "bot://"


def bot_registry_path(account_id: int) -> str:
    """Sentinel stored in worker_registry.session_path for bot accounts."""
    return f"{BOT_REGISTRY_PREFIX}{account_id}"


def is_bot_registry_path(session_path: str | None) -> bool:
    return isinstance(session_path, str) and session_path.startswith(BOT_REGISTRY_PREFIX)


def build_run_worker_argv(
    *,
    user_id: int,
    account_id: int,
    session_path: str,
    python_exe: str,
    project_root: Path,
) -> list[str]:
    """CLI argv for a worker subprocess. Never includes a bot token."""
    cmd = [python_exe, "-m", "app.main", "db", "run-worker", str(user_id)]
    if is_bot_registry_path(session_path):
        cmd.extend(["--account-id", str(account_id)])
        return cmd
    path = Path(session_path)
    session_abs = path.resolve() if path.is_absolute() else (project_root / path).resolve()
    cmd.extend([str(session_abs), "--account-id", str(account_id)])
    return cmd
