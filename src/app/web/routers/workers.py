"""Workers API routes - manage Telegram sync worker processes."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, status

from app.web.deps import CurrentUser, Db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workers", tags=["workers"])

# In-memory registry: worker_id -> {user_id, account_id, session_path, process?, pid, ...}
# process may be None for reattached workers (orphans from prior API run)
_workers: dict[str, dict[str, Any]] = {}
_worker_counter = 0


def _is_process_alive(w: dict[str, Any]) -> bool:
    """Check if a worker process is still running."""
    proc = w.get("process")
    if proc is not None:
        return proc.poll() is None
    pid = w.get("pid")
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _terminate_worker(w: dict[str, Any]) -> None:
    """Terminate a worker process (managed or reattached)."""
    proc = w.get("process")
    pid = w.get("pid")
    if proc is not None and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    elif pid is not None:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass


async def _prune_dead_workers(db: aiosqlite.Connection) -> None:
    """Remove dead workers from the registry and worker_registry table."""
    dead = [wid for wid, w in _workers.items() if not _is_process_alive(w)]
    for wid in dead:
        del _workers[wid]
        await db.execute("DELETE FROM worker_registry WHERE worker_id = ?", (wid,))
    if dead:
        await db.commit()


async def _prune_orphaned_registry_rows(db: aiosqlite.Connection) -> None:
    """Remove worker_registry rows whose PIDs are no longer running (e.g. worker crashed, API
    restarted). This prevents 'Worker already running' when the process is actually dead."""
    async with db.execute(
        "SELECT worker_id, pid FROM worker_registry"
    ) as cur:
        rows = await cur.fetchall()
    deleted = 0
    for worker_id, pid in rows:
        try:
            os.kill(pid, 0)
        except OSError:
            await db.execute("DELETE FROM worker_registry WHERE worker_id = ?", (worker_id,))
            deleted += 1
    if deleted:
        await db.commit()
        logger.info("Pruned %d orphaned worker_registry row(s)", deleted)


def _next_worker_id() -> str:
    global _worker_counter
    _worker_counter += 1
    return f"w{_worker_counter}"


def _account_has_running_worker(account_id: int) -> bool:
    """Check if any running worker exists for this account."""
    for w in _workers.values():
        if w.get("account_id") == account_id and _is_process_alive(w):
            return True
    return False


async def _spawn_worker_for_account(
    db: aiosqlite.Connection,
    account_id: int,
    user_id: int,
    session_path: str,
) -> bool:
    """Spawn a worker process for an account. Returns True if spawned."""
    if _account_has_running_worker(account_id):
        return False
    project_root = Path(__file__).resolve().parents[4]
    session_abs = (project_root / session_path).resolve() if not Path(session_path).is_absolute() else Path(session_path)
    worker_id = _next_worker_id()
    cmd = [
        sys.executable, "-m", "app.main",
        "db", "run-worker",
        str(user_id),
        str(session_abs),
        "--account-id", str(account_id),
    ]
    worker_log_dir = project_root / "data"
    worker_log_dir.mkdir(parents=True, exist_ok=True)
    stderr_path = worker_log_dir / f"worker_{account_id}_{worker_id}.log"
    try:
        stderr_handle = open(stderr_path, "w", encoding="utf-8")
    except OSError:
        stderr_handle = None
    proc = subprocess.Popen(
        cmd,
        cwd=str(project_root),
        stdout=subprocess.DEVNULL,
        stderr=stderr_handle if stderr_handle else subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )
    pid = proc.pid
    started_at = datetime.now(timezone.utc).isoformat()
    _workers[worker_id] = {
        "id": worker_id,
        "user_id": user_id,
        "account_id": account_id,
        "session_path": session_path,
        "process": proc,
        "pid": pid,
        "started_at": started_at,
    }
    await db.execute(
        "INSERT INTO worker_registry (worker_id, user_id, account_id, session_path, pid) VALUES (?, ?, ?, ?, ?)",
        (worker_id, user_id, account_id, session_path, pid),
    )
    await db.commit()
    logger.info("Spawned worker %s for account_id=%s pid=%s", worker_id, account_id, pid)
    return True


async def stop_workers_for_account(account_id: int, db: aiosqlite.Connection) -> None:
    """Internal helper: stop and remove all workers for a given account_id."""
    to_stop = [wid for wid, w in _workers.items() if w.get("account_id") == account_id]
    for wid in to_stop:
        w = _workers[wid]
        _terminate_worker(w)
        del _workers[wid]
        await db.execute("DELETE FROM worker_registry WHERE worker_id = ?", (wid,))
    if to_stop:
        await db.commit()


async def restart_workers_for_mapping(
    db: aiosqlite.Connection,
    mapping_user_id: int,
    mapping_telegram_account_id: int | None,
) -> None:
    """Restart workers affected by a mapping change. If no worker is running for an account
    that has mappings, start one so forwarding begins without manual Worker Start."""
    try:
        await _prune_dead_workers(db)
        await _prune_orphaned_registry_rows(db)
        if mapping_telegram_account_id is not None:
            account_ids = [mapping_telegram_account_id]
        else:
            async with db.execute(
                "SELECT id FROM telegram_accounts WHERE user_id = ? AND status = 'active' "
                "AND session_path IS NOT NULL AND session_path != ''",
                (mapping_user_id,),
            ) as cur:
                rows = await cur.fetchall()
            account_ids = [r[0] for r in rows]
        for account_id in account_ids:
            async with db.execute(
                "SELECT user_id, session_path FROM telegram_accounts WHERE id = ? AND status = 'active'",
                (account_id,),
            ) as cur:
                acc_row = await cur.fetchone()
            if not acc_row or not acc_row[1]:
                continue
            user_id, session_path = acc_row[0], acc_row[1]
            if _account_has_running_worker(account_id):
                await stop_workers_for_account(account_id, db)
            # NOTE: There is an intentional race condition here. Another process may start
            # a worker for this account between the check above and the one below.
            # This is acceptable: failures are caught and logged as warnings rather than
            # propagated, and occasional redundant start/stop attempts are tolerated.
            try:
                if not _account_has_running_worker(account_id):
                    await _spawn_worker_for_account(db, account_id, user_id, session_path)
            except Exception as e:
                logger.warning(
                    "Failed to start/restart worker for account %s after mapping change: %s",
                    account_id,
                    e,
                )
    except Exception as e:
        logger.warning("restart_workers_for_mapping failed: %s", e)


@router.get("")
async def list_workers(user: CurrentUser, db: Db) -> list[dict]:
    """List running workers. Dead workers are pruned from the registry."""
    await _prune_dead_workers(db)
    if user["role"] != "admin":
        items = [w for w in _workers.values() if w["user_id"] == user["id"]]
    else:
        items = list(_workers.values())
    return [
        {
            "id": w["id"],
            "user_id": w["user_id"],
            "account_id": w.get("account_id"),
            "session_path": w["session_path"],
            "pid": w.get("pid") if _is_process_alive(w) else None,
            "running": _is_process_alive(w),
            "started_at": w.get("started_at"),
        }
        for w in items
    ]


@router.post("/start")
async def start_worker(
    user: CurrentUser,
    db: Db,
    account_id: int,
    user_id: int | None = None,
) -> dict:
    """Start a worker for a Telegram account. Users start own; admins can pass user_id."""
    target_user = user["id"]
    if user["role"] == "admin" and user_id is not None:
        target_user = user_id
    if user["role"] != "admin" and target_user != user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot start worker for another user",
        )
    async with db.execute(
        "SELECT id, user_id, session_path, type FROM telegram_accounts WHERE id = ? AND status = 'active'",
        (account_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row or row[1] != target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )
    if row[2] is None or row[2] == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account has no session path (bot accounts cannot run workers)",
        )
    await _prune_dead_workers(db)
    await _prune_orphaned_registry_rows(db)
    session_path = row[2]
    # Check in-memory registry
    if _account_has_running_worker(account_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Worker already running for this account",
        )
    # Check persistent registry (orphans from prior API run). Prune dead entries.
    async with db.execute(
        "SELECT worker_id, pid FROM worker_registry WHERE account_id = ?", (account_id,)
    ) as cur:
        reg_rows = await cur.fetchall()
    for worker_id, reg_pid in reg_rows:
        try:
            os.kill(reg_pid, 0)
        except OSError:
            # Process is dead; remove stale row so we can start a new worker
            await db.execute("DELETE FROM worker_registry WHERE worker_id = ?", (worker_id,))
            continue
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Worker already running for this account",
        )
    if reg_rows:
        await db.commit()
    spawned = await _spawn_worker_for_account(db, account_id, target_user, session_path)
    if not spawned:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Worker already running for this account",
        )
    w = next(x for x in _workers.values() if x["account_id"] == account_id)
    return {
        "id": w["id"],
        "user_id": target_user,
        "account_id": account_id,
        "session_path": session_path,
        "pid": w["pid"],
        "started_at": w.get("started_at"),
    }


@router.post("/{worker_id}/stop")
async def stop_worker(
    worker_id: str,
    user: CurrentUser,
    db: Db,
) -> dict:
    """Stop a running worker."""
    if worker_id not in _workers:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")
    w = _workers[worker_id]
    if user["role"] != "admin" and w["user_id"] != user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    _terminate_worker(w)
    del _workers[worker_id]
    await db.execute("DELETE FROM worker_registry WHERE worker_id = ?", (worker_id,))
    await db.commit()
    return {"status": "ok"}


async def restore_workers_from_db(db: aiosqlite.Connection) -> None:
    """Restore workers from worker_registry. Reattach orphans (alive PIDs); for dead PIDs
    (e.g. after graceful shutdown), spawn new workers. Only accounts that had workers get them back."""
    global _worker_counter
    async with db.execute(
        "SELECT worker_id, user_id, account_id, session_path, pid, created_at FROM worker_registry"
    ) as cur:
        rows = await cur.fetchall()
    max_num = 0
    for row in rows:
        worker_id, user_id, account_id, session_path, pid = row[0], row[1], row[2], row[3], row[4]
        created_at = row[5]
        try:
            os.kill(pid, 0)
        except OSError:
            await db.execute("DELETE FROM worker_registry WHERE worker_id = ?", (worker_id,))
            await _spawn_worker_for_account(db, account_id, user_id, session_path)
            continue
        # Normalize SQLite datetime to ISO UTC for frontend
        started_at = created_at
        if created_at and "T" not in created_at and "Z" not in created_at and "+" not in created_at:
            started_at = created_at.replace(" ", "T") + "Z"
        _workers[worker_id] = {
            "id": worker_id,
            "user_id": user_id,
            "account_id": account_id,
            "session_path": session_path,
            "process": None,
            "pid": pid,
            "started_at": started_at,
        }
        if worker_id.startswith("w") and worker_id[1:].isdigit():
            max_num = max(max_num, int(worker_id[1:]))
    _worker_counter = max_num
    await db.commit()


async def terminate_all_workers(db: aiosqlite.Connection) -> None:
    """Terminate all workers on API shutdown. Keep worker_registry rows so restore can
    spawn workers for these accounts on next startup."""
    to_stop = list(_workers.items())
    for wid, w in to_stop:
        _terminate_worker(w)
        del _workers[wid]
    if to_stop:
        await db.commit()
