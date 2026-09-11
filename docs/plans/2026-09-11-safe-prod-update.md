# Plan: Safe production update for 2026-09-11 changes

**Date:** 2026-09-11  
**Status:** Guidance (ops)  
**Related commits (local `main`, ahead of `origin/main`):**

| Commit | Change |
|--------|--------|
| `2d8dded` | API key scopes + panel |
| `647fd18` | Mapping clone + alert webhooks UI |
| `d6ae181` | Mongo 30-day TTL on message/worker logs |
| `7b167c5` | Admin invites + `docs/plans` workflow |

## Verdict

**Not safe to run the update script yet** until those commits are on the remote the VPS/GHCR pull from.

Local branch: `main` is **ahead 4** of `origin/main`.  
`scripts/update-vps.sh` does `git reset --hard origin/main` — if you run it before push, prod stays on old code (or you think you updated and did not).

Docker multi-env (`deploy/scripts/deploy-env.sh prod`) pulls **GHCR images**, which only rebuild after CI publish on pushed `main`. Same gate: **push first**.

**Follow-up (Done):** `update-vps.sh` now runs `backup-vps-data.sh` before pull (SQLite, sessions, media, `.env`, `data/` tree; optional Mongo). See [Auto-backup in update-vps.sh](2026-09-11-update-vps-auto-backup.md). First VPS update after that lands should refresh scripts or manually copy `data/` once (old script has no backup call).

## What can break (and how we stay safe)

| Change | Risk | Mitigation |
|--------|------|------------|
| SQLite migration **v25** (admin invites schema) | Auto-runs on API start via `init_sqlite` / migrations | Brief restart; backup SQLite file first. Empty/legacy invite rows copied to `token_hash` (table was unused in product). |
| Mongo TTL 30d | Old `message_logs` / `worker_logs` older than 30d deleted after TTL index ensures | Accept retention policy; backup Mongo if you need longer history. Restart API so `ensure_mongo_indexes` upgrades legacy `ix_timestamp`. |
| API key scopes | Existing keys with only `mappings:*` get **403** on workers/logs/etc. | Before cutover: list keys in panel; recreate with needed scopes, or warn operators. |
| Clone / alert webhooks / invites UI | Additive | No break. |
| `update-vps.sh` `git reset --hard` | Discards uncommitted changes on VPS | Ensure no hotfixes only on server; secrets stay in `.env` outside reset if not committed (standard). |

**Workers:** API restart terminates/restores workers (existing lifespan behavior). Expect short copy gap; sessions on disk are preserved.

## Safe order (Ubuntu / `update-vps.sh`)

1. **Backup** on the VPS (or host with volume access):
   - SQLite file (`SQLITE_PATH`, often under `/opt/telegram-copier/data` or `/app/data`)
   - Sessions dir
   - Optional: Mongo dump if TTL loss matters
2. **Push** local `main` to `origin` (requires your approval / credentials).
3. Wait for **CI green** (and GHCR publish if you use Docker images).
4. On VPS:
   ```bash
   sudo bash /opt/telegram-copier/scripts/update-vps.sh
   ```
5. **Verify:**
   ```bash
   sudo systemctl status telegram-copier
   curl -s http://127.0.0.1:8000/health
   ```
   - Log into panel; smoke: mappings list, one worker start/stop, API keys page, invite optional.
6. Optional explicit migrate (if you want belt-and-suspenders before traffic):
   ```bash
   cd /opt/telegram-copier && sudo -u tgcopier .venv/bin/tg-copier db init-db
   ```
   (`update-vps.sh` does **not** call `init-db`; migrations normally apply on app boot.)

## Safe order (Docker multi-env prod)

1. Backup named volume / bind mount for `tgc-prod_app_data` (and mongo if needed).
2. Push `main` → wait for publish workflow → note `sha-…` or `latest`.
3. Prefer pin on first prod roll:
   ```bash
   ./deploy/scripts/deploy-env.sh prod sha-<7char>
   ```
   (or `latest` after you trust the image).
4. Health + smoke as above via compose `exec` / published port.

## Do not

- Run `update-vps.sh` before push (no new code).
- Skip backup if the SQLite file is the only tenancy store.
- Expect old API keys with narrow scopes to keep full access after deploy.

## Confirmed topology

**Native VPS** — use `sudo bash /opt/telegram-copier/scripts/update-vps.sh` only (ignore Docker / GHCR path above).

Push to origin only when you explicitly ask.
