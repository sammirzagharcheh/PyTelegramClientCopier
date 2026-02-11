"""Workers API routes - manage Telegram sync worker processes."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.web.deps import CurrentUser, Db

router = APIRouter(prefix="/workers", tags=["workers"])

# In-memory registry: worker_id -> {user_id, session_path, process, ...}
_workers: dict[str, dict[str, Any]] = {}
_worker_counter = 0


def _prune_dead_workers() -> None:
    """Remove dead workers from the registry."""
    dead = [wid for wid, w in _workers.items() if w["process"].poll() is not None]
    for wid in dead:
        del _workers[wid]


def _next_worker_id() -> str:
    global _worker_counter
    _worker_counter += 1
    return f"w{_worker_counter}"


def stop_workers_for_account(account_id: int) -> None:
    """Internal helper: stop and remove all workers for a given account_id."""
    to_stop = [wid for wid, w in _workers.items() if w.get("account_id") == account_id]
    for wid in to_stop:
        w = _workers[wid]
        proc = w["process"]
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        del _workers[wid]


@router.get("")
async def list_workers(user: CurrentUser) -> list[dict]:
    """List running workers. Dead workers are pruned from the registry."""
    _prune_dead_workers()
    if user["role"] != "admin":
        items = [w for w in _workers.values() if w["user_id"] == user["id"]]
    else:
        items = list(_workers.values())
    return [
        {
            "id": w["id"],
            "user_id": w["user_id"],
            "session_path": w["session_path"],
            "pid": w["process"].pid if w["process"].poll() is None else None,
            "running": w["process"].poll() is None,
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
    _prune_dead_workers()
    session_path = row[2]
    for w in _workers.values():
        if w["user_id"] == target_user and w["session_path"] == session_path:
            if w["process"].poll() is None:
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
    _workers[worker_id] = {
        "id": worker_id,
        "user_id": target_user,
        "account_id": account_id,
        "session_path": row[2],
        "process": proc,
    }
    return {
        "id": worker_id,
        "user_id": target_user,
        "account_id": account_id,
        "session_path": row[2],
        "pid": proc.pid,
    }


@router.post("/{worker_id}/stop")
async def stop_worker(
    worker_id: str,
    user: CurrentUser,
) -> dict:
    """Stop a running worker."""
    if worker_id not in _workers:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")
    w = _workers[worker_id]
    if user["role"] != "admin" and w["user_id"] != user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    proc = w["process"]
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    del _workers[worker_id]
    return {"status": "ok"}
