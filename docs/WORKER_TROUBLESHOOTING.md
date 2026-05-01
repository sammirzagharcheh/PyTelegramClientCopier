# Worker Troubleshooting Guide

## Why a worker stops and cannot be restarted

### Root cause fixed: stale `worker_registry` rows

When a worker process stops, its row in `worker_registry` (PostgreSQL) can remain. On restart:

1. `start_worker` checks `worker_registry` for the account
2. If it finds a row, it uses `os.kill(pid, 0)` to see if the process is still alive
3. **Previous bug**: When the process was dead (OSError), we continued without deleting the row
4. This could lead to "Worker already running" in edge cases (e.g. PID recycling), or stale data

**Fix applied**: Dead entries in `worker_registry` are now deleted when you try to start a worker, so a new worker can be spawned.

### Admin recovery endpoint for 409 conflicts

If `/api/workers/start` returns `409 Conflict` and you need to forcibly clear stale rows for one account:

`POST /api/workers/reset-account?account_id=<ID>`

- Admin token required.
- Stops alive worker PIDs for that account.
- Clears reservation/stale rows in `worker_registry`.
- Returns counts: `stopped_workers`, `cleared_rows`.

---

## Diagnosing why workers stop: MongoDB `worker_logs`

The `worker_logs` collection stores: `user_id`, `account_id`, `level`, `message`, `timestamp`.

### Useful MongoDB queries

**Last 100 worker log entries (all accounts):**
```javascript
db.worker_logs.find().sort({ timestamp: -1 }).limit(100)
```

**Recent ERROR/WARNING for a specific account:**
```javascript
db.worker_logs.find(
  { account_id: YOUR_ACCOUNT_ID, level: { $in: ["ERROR", "WARNING"] } }
).sort({ timestamp: -1 }).limit(50)
```

**Logs in the last 24 hours:**
```javascript
const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000);
db.worker_logs.find({ timestamp: { $gte: yesterday } }).sort({ timestamp: -1 })
```

**Last log before worker disappeared:**
```javascript
db.worker_logs.find({ account_id: YOUR_ACCOUNT_ID })
  .sort({ timestamp: -1 }).limit(20)
```

---

## Common reasons workers stop

| Reason | What to look for in logs |
|--------|---------------------------|
| **Session conflict / AuthKeyDuplicated** | Telethon disconnects when the same session is used elsewhere. Look for disconnect/auth messages. |
| **Database errors** | PostgreSQL transaction/connection errors during worker actions. Check API logs and DB connectivity. |
| **Session copy failed** | Fallback to shared session can cause conflicts. Look for `Could not copy session to worker path`. |
| **Telegram disconnect** | Network issues, FloodWait, or server-side disconnect. Check for disconnect/connection errors. |
| **Unhandled exception** | Python tracebacks in ERROR-level logs. |
| **OOM / process killed** | Worker process killed by OS. Last log may be normal; check system logs. |

---

## File-based logs

Workers also write to `data/worker.log` and per-worker stderr files:
`data/worker_{account_id}_{worker_id}.log`

Check these if MongoDB logs are empty (e.g. MongoDB down when the worker ran).

---

## Edit and delete sync (`sync_edits` / `sync_deletes`)

When these mapping flags are enabled, the worker tries to mirror source message edits and deletions to the destination using the stored `dest_message_index` (source message id → destination message id).

- **Permissions:** The Telegram account running the worker must be allowed to edit or delete messages in the destination chat (e.g. admin with “Edit messages of others” / “Delete messages of others” where applicable).
- **`append_notice` edit strategy:** If in-place `edit_message` fails (common for media-only or non-editable posts), set **Edit strategy** to **Append notice** on the mapping so edits become a new text message instead of editing the original destination message.
- **Albums / grouped media:** Telegram may deliver separate events per album item; behavior depends on how messages were indexed when copied. If deletes or edits miss some items, consider treating albums as a known limitation or adjust mapping usage.
- **Logs:** Failed `edit_message` / `delete_messages` calls are logged at **WARNING** with `mapping_id` when sync is enabled so they appear in worker logs (e.g. Mongo `worker_logs` and file logs).

If the source `chat_id` from Telegram does not match the configured `source_chat_id` (rare peer/channel id variants), the worker normalizes using both `event.chat_id` and `event.peer` where possible; if nothing matches your mapping, the edit/delete is skipped silently.
