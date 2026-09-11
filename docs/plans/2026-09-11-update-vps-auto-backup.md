# Plan: Auto-backup in `update-vps.sh`

**Date:** 2026-09-11  
**Status:** Done  
**Related:** [Safe production update](2026-09-11-safe-prod-update.md)

## What / why

Today `scripts/update-vps.sh` pulls, rebuilds, and restarts with **no backup**. Operators must remember to copy `data/` first. A failed migration, bad release, or fat-finger is harder to undo without a snapshot.

**Recommendation: yes — add automatic backups before any destructive/update step**, with retention and an escape hatch.

## Architectural impact

- **No change** to runtime architecture (`docs/architecture.md` invariants unchanged).
- Ops-only: Ubuntu native update path (`deploy-ubuntu.md` / update script).
- SQLite remains SoR for tenancy/config/reply index; sessions remain on disk under `SESSIONS_DIR`. Mongo stays soft-fail observability — backup optional.

## What to back up (priority)

| Asset | Required? | Why |
|-------|-----------|-----|
| SQLite file (`SQLITE_PATH`, usually under `$INSTALL_DIR/data`) | **Yes** | Tenancy, mappings, auth, reply index |
| Sessions dir (`SESSIONS_DIR`) | **Yes** | Telegram login state; losing it forces re-auth |
| Media assets (`MEDIA_ASSETS_DIR`) | Yes (cheap if small) | Transform/upload assets |
| App `.env` (secrets; never commit) | **Yes** (copy into backup dir with mode `600`) | Recover install config after mishap |
| MongoDB dump | **Optional / opt-in** | Logs only; TTL already 30d; dump is slow/heavy |

Default: tar (or `cp -a`) of `data/` + `.env` into e.g. `$INSTALL_DIR/backups/pre-update-YYYYMMDD-HHMMSS/` or `/var/backups/telegram-copier/…`.

## Behavior

1. Resolve paths from env file if present (`$INSTALL_DIR/.env`: `SQLITE_PATH`, `SESSIONS_DIR`, `MEDIA_ASSETS_DIR`), else defaults under `$INSTALL_DIR/data`.
2. **Before** `git fetch` / `reset --hard`: create timestamped backup; print path.
3. Fail the update if backup fails (`set -e`) — do not proceed blind.
4. Retention: keep last **N** backups (default `BACKUP_KEEP=5`); prune older.
5. Flags / env:
   - `SKIP_BACKUP=1` — escape hatch for emergencies / CI-like nodes
   - `BACKUP_MONGO=1` — optional `mongodump` when `mongod`/`mongosh` available and `NO_MONGO` not set
   - `BACKUP_DIR` — override destination
6. Do **not** put backups inside a path that `git reset --hard` can delete if they live under a tracked tree; prefer `$INSTALL_DIR/backups/` (gitignored) or `/var/backups/…`.

## Risks + mitigations

| Risk | Mitigation |
|------|------------|
| Disk full from backups | Cap `BACKUP_KEEP`; document size; fail early with clear message |
| Backup includes secrets (`.env`) | Restrict dir perms (`750`/`700`); never upload backups to git |
| Long backup delays update | Prefer `cp -a`/`tar` of `data/` only; Mongo opt-in |
| Paths wrong if custom `SQLITE_PATH` outside `data/` | Read `.env`; always include resolved SQLite + sessions paths explicitly |
| False safety (backup != tested restore) | Doc one restore recipe in `deploy-ubuntu.md` |

## Doc updates required

- `docs/deploy-ubuntu.md` — update section: script now backs up; how to skip; how to restore
- `docs/plans/2026-09-11-safe-prod-update.md` — note auto-backup once shipped
- Ensure `backups/` in `.gitignore` if under install dir / repo
- Architecture: **no SoT change** (optional one-line under ops/deploy if §12 maps it)

## Test plan

- Shellcheck / dry-run logic where possible
- Manual: temp dir with fake `data/app.db` + sessions → run backup function → assert archive exists and prune keeps N
- Optional small bash test under `tests/` or `scripts/` if we extract a `backup-vps-data.sh` helper
- Confirm `SKIP_BACKUP=1` skips and continues

## Implementation order

1. Add `.gitignore` entry for `backups/` (if needed).
2. Implement backup + prune in `update-vps.sh` (or shared `scripts/backup-vps-data.sh` called first).
3. Update `deploy-ubuntu.md` restore/update docs.
4. Touch safe-prod plan status note.
5. No Python/pytest required unless we add a pure helper worth unit-testing.

## Out of scope

- Docker `deploy-env.sh` auto-backup (separate follow-up; volumes differ).
- Off-box / S3 replication (nice later; not required for “don’t break me on update”).
