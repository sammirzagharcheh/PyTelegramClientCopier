"""Workers API routes - manage Telegram sync worker processes."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, status

from app.web.deps import CurrentUser, Db

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


def _next_worker_id() -> str:
    global _worker_counter
    _worker_counter += 1
    return f"w{_worker_counter}"


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
            "session_path": w["session_path"],
            "pid": w.get("pid") if _is_process_alive(w) else None,
            "running": _is_process_alive(w),
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
    session_path = row[2]
    # Check in-memory registry
    for w in _workers.values():
        if w["user_id"] == target_user and w["session_path"] == session_path:
            if _is_process_alive(w):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Worker already running for this account",
                )
    # Check persistent registry (orphans from prior API run)
    async with db.execute(
        "SELECT pid FROM worker_registry WHERE account_id = ?", (account_id,)
    ) as cur:
        reg_rows = await cur.fetchall()
    for (reg_pid,) in reg_rows:
        try:
            os.kill(reg_pid, 0)
        except OSError:
            continue
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Worker already running for this account",
        )
    project_root = Path(__file__).resolve().parents[4]
    session_abs = (project_root / session_path).resolve() if not Path(session_path).is_absolute() else Path(session_path)
    worker_id = _next_worker_id()
    cmd = [
        sys.executable, "-m", "app.main",
        "db", "run-worker",
        str(target_user),
        str(session_abs),
        "--account-id", str(account_id),
    ]
    proc = subprocess.Popen(
        cmd,
        cwd=str(project_root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )
    pid = proc.pid
    _workers[worker_id] = {
        "id": worker_id,
        "user_id": target_user,
        "account_id": account_id,
        "session_path": row[2],
        "process": proc,
        "pid": pid,
    }
    await db.execute(
        "INSERT INTO worker_registry (worker_id, user_id, account_id, session_path, pid) VALUES (?, ?, ?, ?, ?)",
        (worker_id, target_user, account_id, row[2], pid),
    )
    await db.commit()
    return {
        "id": worker_id,
        "user_id": target_user,
        "account_id": account_id,
        "session_path": row[2],
        "pid": pid,
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
    """Restore orphan workers from worker_registry after API restart."""
    global _worker_counter
    async with db.execute(
        "SELECT worker_id, user_id, account_id, session_path, pid FROM worker_registry"
    ) as cur:
        rows = await cur.fetchall()
    max_num = 0
    for worker_id, user_id, account_id, session_path, pid in rows:
        try:
            os.kill(pid, 0)
        except OSError:
            await db.execute("DELETE FROM worker_registry WHERE worker_id = ?", (worker_id,))
            continue
        _workers[worker_id] = {
            "id": worker_id,
            "user_id": user_id,
            "account_id": account_id,
            "session_path": session_path,
            "process": None,
            "pid": pid,
        }
        if worker_id.startswith("w") and worker_id[1:].isdigit():
            max_num = max(max_num, int(worker_id[1:]))
    _worker_counter = max_num
    if rows:
        await db.commit()


async def terminate_all_workers(db: aiosqlite.Connection) -> None:
    """Terminate all workers on API shutdown."""
    to_stop = list(_workers.items())
    for wid, w in to_stop:
        _terminate_worker(w)
        del _workers[wid]
    if to_stop:
        await db.execute("DELETE FROM worker_registry")
        await db.commit()
