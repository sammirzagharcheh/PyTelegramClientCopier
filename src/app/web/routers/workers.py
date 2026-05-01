"""Workers API routes - manage Telegram sync worker processes."""

from __future__ import annotations

import asyncio
import contextlib
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

from app.db.postgres import retry_transient_postgres, using_postgres
from app.web.deps import AdminUser, CurrentUser, Db, WriterUser

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workers", tags=["workers"])

# In-memory registry: worker_id -> {user_id, account_id, session_path, process?, pid, ...}
# process may be None for reattached workers (orphans from prior API run)
_workers: dict[str, dict[str, Any]] = {}
_worker_counter = 0
_account_worker_locks: dict[int, asyncio.Lock] = {}
_account_worker_locks_guard = asyncio.Lock()


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


async def _terminate_worker(w: dict[str, Any]) -> None:
    """Terminate a worker process (managed or reattached). Waits for exit before returning."""
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
            await _wait_for_pid_exit(pid, timeout_sec=5.0)
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


def _pid_alive(pid: int) -> bool:
    """Check if a process with the given PID is alive."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _is_starting_reservation_pid(pid: int | None) -> bool:
    """True when worker row is a reserved-but-not-launched slot."""
    return isinstance(pid, int) and pid <= 0


async def _wait_for_pid_exit(pid: int, timeout_sec: float = 5.0) -> bool:
    """Poll until process exits or timeout. Returns True if exited within timeout."""
    polls = int(timeout_sec / 0.1) or 1
    for _ in range(polls):
        try:
            os.kill(pid, 0)
        except OSError:
            return True  # Process is gone
        await asyncio.sleep(0.1)
    return False


async def _get_account_worker_lock(account_id: int) -> asyncio.Lock:
    """Return a stable per-account lock for worker start/restart operations."""
    async with _account_worker_locks_guard:
        lock = _account_worker_locks.get(account_id)
        if lock is None:
            lock = asyncio.Lock()
            _account_worker_locks[account_id] = lock
        return lock


async def _list_workers_from_registry(
    db: aiosqlite.Connection, user: dict
) -> tuple[list[dict], int, int, int]:
    """
    List workers from worker_registry (source of truth). Prunes dead PIDs, reattaches
    alive workers missing from _workers, and returns the response list.
    Returns (items, workers_in_registry, workers_reattached, workers_pruned).
    """
    if user["role"] != "admin":
        async with db.execute(
            "SELECT worker_id, user_id, account_id, session_path, pid, created_at, last_heartbeat_at "
            "FROM worker_registry WHERE user_id = ?",
            (user["id"],),
        ) as cur:
            rows = await cur.fetchall()
    else:
        async with db.execute(
            "SELECT worker_id, user_id, account_id, session_path, pid, created_at, last_heartbeat_at "
            "FROM worker_registry"
        ) as cur:
            rows = await cur.fetchall()

    workers_in_registry = len(rows)
    workers_reattached = 0
    workers_pruned = 0
    items: list[dict] = []

    for row in rows:
        worker_id, uid, account_id, session_path, pid, created_at, last_heartbeat_at = (
            row[0], row[1], row[2], row[3], row[4], row[5], row[6] if len(row) > 6 else None
        )
        if _is_starting_reservation_pid(pid):
            # Hide in-progress reservations from "running workers" listings.
            continue
        if not _pid_alive(pid):
            await db.execute("DELETE FROM worker_registry WHERE worker_id = ?", (worker_id,))
            workers_pruned += 1
            continue

        # Normalize SQLite datetime to ISO UTC for frontend
        started_at = created_at
        if created_at and "T" not in str(created_at) and "Z" not in str(created_at) and "+" not in str(created_at):
            started_at = str(created_at).replace(" ", "T") + "Z"

        # Reattach to _workers if missing (e.g. worker started by another API instance)
        if worker_id not in _workers:
            _workers[worker_id] = {
                "id": worker_id,
                "user_id": uid,
                "account_id": account_id,
                "session_path": session_path,
                "process": None,
                "pid": pid,
                "started_at": started_at,
            }
            workers_reattached += 1

        hb = last_heartbeat_at
        if hb and "T" not in str(hb) and "Z" not in str(hb) and "+" not in str(hb):
            hb = str(hb).replace(" ", "T") + "Z"
        items.append({
            "id": worker_id,
            "user_id": uid,
            "account_id": account_id,
            "session_path": session_path,
            "pid": pid,
            "running": True,
            "started_at": started_at,
            "last_heartbeat_at": hb,
        })

    if workers_pruned:
        await db.commit()

    return items, workers_in_registry, workers_reattached, workers_pruned


async def _prune_orphaned_registry_rows(db: aiosqlite.Connection) -> None:
    """Remove worker_registry rows whose PIDs are no longer running (e.g. worker crashed, API
    restarted). This prevents 'Worker already running' when the process is actually dead."""
    async with db.execute(
        "SELECT worker_id, pid FROM worker_registry"
    ) as cur:
        rows = await cur.fetchall()
    deleted = 0
    for worker_id, pid in rows:
        if _is_starting_reservation_pid(pid):
            # Keep in-flight reservations; another request is still launching the worker.
            continue
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
    """Check if any running worker exists for this account (in-memory)."""
    for w in _workers.values():
        if w.get("account_id") == account_id and _is_process_alive(w):
            return True
    return False


def _running_worker_info_for_account(account_id: int) -> tuple[str | None, int | None]:
    """Return (worker_id, pid) for a live in-memory worker for this account, else (None, None)."""
    for wid, w in _workers.items():
        if w.get("account_id") == account_id and _is_process_alive(w):
            return wid, w.get("pid")
    return None, None


async def _account_has_worker_in_registry(db: aiosqlite.Connection, account_id: int) -> bool:
    """Check if worker_registry has any row for this account with alive PID (covers workers
    started by other API processes)."""
    async with db.execute(
        "SELECT worker_id, pid FROM worker_registry WHERE account_id = ?", (account_id,)
    ) as cur:
        rows = await cur.fetchall()
    for _worker_id, pid in rows:
        if _pid_alive(pid):
            return True
    return False


async def _spawn_worker_for_account(
    db: aiosqlite.Connection,
    account_id: int,
    user_id: int,
    session_path: str,
) -> bool:
    """Spawn a worker process for an account. Returns True if spawned.

    Concurrency safety:
    - serializes starts per account in-process
    - reserves worker_registry row in DB before spawning process
    - relies on UNIQUE(account_id) index to prevent cross-process duplicates
    """
    lock = await _get_account_worker_lock(account_id)
    async with lock:
        if using_postgres():
            # Lock the account row to serialize concurrent cross-process starts.
            async with db.execute(
                "SELECT id FROM telegram_accounts WHERE id = ? FOR UPDATE",
                (account_id,),
            ) as cur:
                await cur.fetchone()

        if _account_has_running_worker(account_id):
            return False

        worker_id = _next_worker_id()

        async def _reserve_worker_slot() -> bool:
            select_sql = "SELECT worker_id, pid FROM worker_registry WHERE account_id = ?"
            if using_postgres():
                select_sql += " FOR UPDATE"
            async with db.execute(select_sql, (account_id,)) as cur:
                rows = await cur.fetchall()
            for existing_worker_id, existing_pid in rows:
                if _is_starting_reservation_pid(existing_pid):
                    return False
                if _pid_alive(existing_pid):
                    return False
                await db.execute(
                    "DELETE FROM worker_registry WHERE worker_id = ?",
                    (existing_worker_id,),
                )
            await db.execute(
                "INSERT INTO worker_registry (worker_id, user_id, account_id, session_path, pid) "
                "VALUES (?, ?, ?, ?, ?)",
                (worker_id, user_id, account_id, session_path, -1),
            )
            await db.commit()
            return True

        try:
            reserved = await retry_transient_postgres(
                _reserve_worker_slot,
                operation_name="workers.reserve_worker_slot",
            )
            if not reserved:
                return False
        except aiosqlite.IntegrityError:
            return False
        except Exception:
            raise

        project_root = Path(__file__).resolve().parents[4]
        session_abs = (project_root / session_path).resolve() if not Path(session_path).is_absolute() else Path(session_path)
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
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(project_root),
                stdout=subprocess.DEVNULL,
                stderr=stderr_handle if stderr_handle else subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
            )
        except Exception:
            # Release reserved row so future retries can proceed.
            await db.execute("DELETE FROM worker_registry WHERE worker_id = ?", (worker_id,))
            await db.commit()
            raise
        pid = proc.pid
        started_at = datetime.now(timezone.utc).isoformat()
        try:
            cur = await db.execute(
                "UPDATE worker_registry SET pid = ? WHERE worker_id = ?",
                (pid, worker_id),
            )
            if cur.rowcount == 0:
                raise RuntimeError("worker_registry reservation disappeared before PID update")
            await db.commit()
        except Exception:
            with contextlib.suppress(Exception):
                proc.terminate()
                proc.wait(timeout=5)
            with contextlib.suppress(Exception):
                await db.execute("DELETE FROM worker_registry WHERE worker_id = ?", (worker_id,))
                await db.commit()
            raise
        _workers[worker_id] = {
            "id": worker_id,
            "user_id": user_id,
            "account_id": account_id,
            "session_path": session_path,
            "process": proc,
            "pid": pid,
            "started_at": started_at,
        }
        logger.info("Spawned worker %s for account_id=%s pid=%s", worker_id, account_id, pid)
        return True


async def stop_workers_for_account(account_id: int, db: aiosqlite.Connection) -> None:
    """Stop and remove all workers for a given account_id. Uses worker_registry as source of
    truth so workers started by other API processes are also stopped. Waits for each process
    to exit before returning."""
    lock = await _get_account_worker_lock(account_id)
    async with lock:
        async with db.execute(
            "SELECT worker_id, user_id, session_path, pid FROM worker_registry WHERE account_id = ?",
            (account_id,),
        ) as cur:
            rows = await cur.fetchall()
        for worker_id, uid, session_path, pid in rows:
            if _is_starting_reservation_pid(pid):
                # Preserve reservation rows; launcher will finalize or clean up.
                continue
            if not _pid_alive(pid):
                await db.execute("DELETE FROM worker_registry WHERE worker_id = ?", (worker_id,))
                continue
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                await db.execute("DELETE FROM worker_registry WHERE worker_id = ?", (worker_id,))
                continue
            await _wait_for_pid_exit(pid, timeout_sec=5.0)
            # Force-kill if still alive after wait (SIGKILL not on Windows)
            try:
                os.kill(pid, 0)
                kill_sig = getattr(signal, "SIGKILL", signal.SIGTERM)
                os.kill(pid, kill_sig)
            except OSError:
                pass
            if worker_id in _workers:
                del _workers[worker_id]
            await db.execute("DELETE FROM worker_registry WHERE worker_id = ?", (worker_id,))
        # Also stop any in-memory workers not yet in registry (race)
        to_stop = [wid for wid, w in _workers.items() if w.get("account_id") == account_id]
        for wid in to_stop:
            w = _workers[wid]
            await _terminate_worker(w)
            del _workers[wid]
            await db.execute("DELETE FROM worker_registry WHERE worker_id = ?", (wid,))
        if rows or to_stop:
            await db.commit()


@router.post("/reset-account")
async def reset_worker_account(
    user: AdminUser,
    db: Db,
    account_id: int,
) -> dict:
    """Admin recovery endpoint: stop worker process(es) and clear registry rows for account."""
    lock = await _get_account_worker_lock(account_id)
    stopped_workers = 0
    cleared_rows = 0
    async with lock:
        async with db.execute(
            "SELECT worker_id, pid FROM worker_registry WHERE account_id = ?",
            (account_id,),
        ) as cur:
            rows = await cur.fetchall()

        for worker_id, pid in rows:
            if _is_starting_reservation_pid(pid):
                await db.execute("DELETE FROM worker_registry WHERE worker_id = ?", (worker_id,))
                if worker_id in _workers:
                    del _workers[worker_id]
                cleared_rows += 1
                continue

            if _pid_alive(pid):
                try:
                    os.kill(pid, signal.SIGTERM)
                    await _wait_for_pid_exit(pid, timeout_sec=5.0)
                    try:
                        os.kill(pid, 0)
                        kill_sig = getattr(signal, "SIGKILL", signal.SIGTERM)
                        os.kill(pid, kill_sig)
                    except OSError:
                        pass
                    stopped_workers += 1
                except OSError:
                    pass
            else:
                cleared_rows += 1

            if worker_id in _workers:
                del _workers[worker_id]
            await db.execute("DELETE FROM worker_registry WHERE worker_id = ?", (worker_id,))

        # Safety net: clear any in-memory workers for this account that lack registry rows.
        to_stop = [wid for wid, w in _workers.items() if w.get("account_id") == account_id]
        for wid in to_stop:
            await _terminate_worker(_workers[wid])
            del _workers[wid]
            await db.execute("DELETE FROM worker_registry WHERE worker_id = ?", (wid,))
            stopped_workers += 1

        if rows or to_stop:
            await db.commit()

    return {
        "status": "ok",
        "account_id": account_id,
        "stopped_workers": stopped_workers,
        "cleared_rows": cleared_rows,
    }


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
            # Always stop first (registry-first stops workers from any API process); ensures
            # no overlap of old and new workers before spawn.
            await stop_workers_for_account(account_id, db)
            try:
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
    """List running workers. Uses worker_registry as source of truth; reattaches workers
    missing from in-memory state. Dead workers are pruned."""
    await _prune_dead_workers(db)
    items, in_registry, reattached, pruned = await _list_workers_from_registry(db, user)
    if reattached > 0 or pruned > 0:
        logger.info(
            "list_workers: registry=%d alive=%d reattached=%d pruned=%d",
            in_registry,
            len(items),
            reattached,
            pruned,
        )
    else:
        logger.debug(
            "list_workers: registry=%d alive=%d",
            in_registry,
            len(items),
        )
    return items


@router.post("/start")
async def start_worker(
    user: WriterUser,
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
        wid, mpid = _running_worker_info_for_account(account_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Worker already running for this account (in-memory worker_id={wid}, pid={mpid}). "
                "Stop that worker from Admin → Workers (or POST /api/workers/{worker_id}/stop) before starting again."
            ),
        )
    # Check persistent registry (orphans from prior API run). Prune dead entries.
    async with db.execute(
        "SELECT worker_id, pid FROM worker_registry WHERE account_id = ?", (account_id,)
    ) as cur:
        reg_rows = await cur.fetchall()
    for worker_id, reg_pid in reg_rows:
        if _is_starting_reservation_pid(reg_pid):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Worker start already in progress for this account. "
                    "Retry after a moment."
                ),
            )
        try:
            os.kill(reg_pid, 0)
        except OSError:
            # Process is dead; remove stale row so we can start a new worker
            await db.execute("DELETE FROM worker_registry WHERE worker_id = ?", (worker_id,))
            continue
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Worker already running for this account (registry worker_id={worker_id}, pid={reg_pid}). "
                "Stop that worker or restart the API after confirming the PID is not a stale zombie."
            ),
        )
    if reg_rows:
        await db.commit()
    spawned = await _spawn_worker_for_account(db, account_id, target_user, session_path)
    if not spawned:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Could not start worker (race or duplicate): another live worker or registry row "
                f"exists for account_id={account_id}. Retry after a moment or stop the existing worker."
            ),
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
    user: WriterUser,
    db: Db,
) -> dict:
    """Stop a running worker."""
    if worker_id not in _workers:
        # Worker may have been listed by another API instance; try to reattach from registry
        async with db.execute(
            "SELECT worker_id, user_id, account_id, session_path, pid, created_at FROM worker_registry WHERE worker_id = ?",
            (worker_id,),
        ) as cur:
            row = await cur.fetchone()
        if row:
            _, uid, account_id, session_path, pid, created_at = row
            if user["role"] != "admin" and uid != user["id"]:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
            if _pid_alive(pid):
                started_at = created_at
                if created_at and "T" not in str(created_at) and "Z" not in str(created_at) and "+" not in str(created_at):
                    started_at = str(created_at).replace(" ", "T") + "Z"
                _workers[worker_id] = {
                    "id": worker_id,
                    "user_id": uid,
                    "account_id": account_id,
                    "session_path": session_path,
                    "process": None,
                    "pid": pid,
                    "started_at": started_at,
                }
            else:
                await db.execute("DELETE FROM worker_registry WHERE worker_id = ?", (worker_id,))
                await db.commit()
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found (already stopped)")
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")
    w = _workers[worker_id]
    if user["role"] != "admin" and w["user_id"] != user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    await _terminate_worker(w)
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
            await db.commit()
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
        await _terminate_worker(w)
        del _workers[wid]
    if to_stop:
        await db.commit()
