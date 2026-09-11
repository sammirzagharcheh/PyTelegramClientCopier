# Plan: Standalone prune-old-VPS-backups script

**Date:** 2026-09-11  
**Status:** Done  
**Related:** [Auto-backup in update-vps.sh](2026-09-11-update-vps-auto-backup.md)

**Config choice:** **A** — `backup.conf` preferred + `.env` fallback + env override; default **10**.

## What / why

`backup-vps-data.sh` already prunes after each update (`BACKUP_KEEP`, currently default **5**). Operators also need a **standalone** cleanup script to:

- Run on a schedule (cron) without updating the app
- Reclaim disk when many manual/extra snapshots accumulate
- Use a clear **default of 10** kept backups, overridable from a **config file**

## Architectural impact

- **No** change to runtime architecture / tenancy / workers (`docs/architecture.md` invariants unchanged).
- Ops-only: Ubuntu VPS scripts + deploy docs.
- Prefer **one shared prune implementation** so update-time prune and cron prune cannot drift.

## Proposed behavior

### New script: `scripts/prune-vps-backups.sh`

```bash
sudo bash /opt/telegram-copier/scripts/prune-vps-backups.sh
# optional:
DRY_RUN=1 sudo bash .../prune-vps-backups.sh
BACKUP_KEEP=3 sudo bash .../prune-vps-backups.sh
```

- Target dirs: `$BACKUP_DIR/pre-update-*` (newest first via `ls -1dt`).
- Delete oldest beyond keep count (`rm -rf`).
- Print what was kept / removed.
- `DRY_RUN=1` — list deletions only, exit 0.
- Refuse `BACKUP_KEEP < 1` (fail with clear error).
- Idempotent if fewer than keep exist.

### Keep-count resolution (highest wins)

| Priority | Source | Example |
|----------|--------|---------|
| 1 | Env / CLI | `BACKUP_KEEP=15` |
| 2 | Config file | see below |
| 3 | Default | **10** |

### Config file (recommended)

Add a small **non-secret** ops file (not the app JWT `.env`), e.g.:

**Path:** `$INSTALL_DIR/backup.conf` (gitignored example committed as `backup.conf.example`)

```bash
# /opt/telegram-copier/backup.conf
BACKUP_KEEP=10
BACKUP_DIR=/opt/telegram-copier/backups
# optional later: BACKUP_MONGO=0
```

Also accept the same keys from `$INSTALL_DIR/.env` if present (operators who already put `BACKUP_KEEP` there), but **document `backup.conf` as the preferred place** so secrets stay separate from retention policy.

Override path: `BACKUP_CONF=/path/to/file`.

### Align update-time backup prune

Change `backup-vps-data.sh` / `update-vps.sh` default `BACKUP_KEEP` from **5 → 10**, and resolve keep via the **same** helper (source shared functions or call `prune-vps-backups.sh` at end of backup).

So: one default, one config story.

### Optional cron (docs only)

Example weekly prune in `deploy-ubuntu.md`:

```cron
0 3 * * 0 root /opt/telegram-copier/scripts/prune-vps-backups.sh >> /var/log/tgc-backup-prune.log 2>&1
```

Not installed automatically by deploy (operator opt-in).

## Risks + mitigations

| Risk | Mitigation |
|------|------------|
| Deletes backups operator still needed | Default 10; `DRY_RUN=1`; document restore path |
| Wrong `BACKUP_DIR` | Resolve same as backup script (`backup.conf` / `.env` / `$INSTALL_DIR/backups`) |
| Config typo `BACKUP_KEEP=0` or empty | Validate integer ≥ 1 |
| Drift between prune-on-backup and standalone | Shared `tgc_prune_backups` + shared keep resolver in one file (source from both scripts) |
| `backup.conf` committed with secrets | Example only; real file gitignored; no secrets in schema |

## Doc updates required

- `docs/deploy-ubuntu.md` — prune script, `backup.conf`, cron example; update BACKUP_KEEP default table 5→10
- `docs/dev-cheatsheet.md` — row for prune script + tests
- `docs/architecture.md` — one-line under Native VPS if needed (optional)
- `backup.conf.example` at repo root or `deploy/` / `scripts/` — prefer `$INSTALL_DIR` copy from `backup.conf.example` next to scripts or repo root
- Plan index status → Done after implement

## Test plan

Extend `tests/unit/test_backup_vps_data.py` (or new `test_prune_vps_backups.py`):

1. Seed 12 fake `pre-update-*` dirs → run prune with default → **10** remain.
2. `backup.conf` with `BACKUP_KEEP=3` → **3** remain.
3. Env `BACKUP_KEEP=4` overrides config file `BACKUP_KEEP=2` → **4** remain.
4. `DRY_RUN=1` → count unchanged.
5. Invalid keep (`0`, `abc`) → non-zero exit, no deletes.

Needs `bash` (same as existing backup tests).

## Implementation order

1. Extract shared helpers (`tgc_env_get`, keep resolver, `tgc_prune_backups`) into e.g. `scripts/vps-backup-lib.sh` **or** keep in `backup-vps-data.sh` and source it from prune (simpler: source backup script’s functions — but backup runs on source; cleaner small `vps-backup-lib.sh`).
2. Add `scripts/prune-vps-backups.sh`.
3. Point `backup-vps-data.sh` at shared keep default **10** + same config resolution.
4. Add `backup.conf.example`; gitignore `backup.conf`.
5. Docs + tests → green.

## Out of scope

- Docker volume prune / GHCR path
- Off-box / S3 retention
- Changing what a backup contains
- Auto-installing cron in `deploy-ubuntu.sh`

## Open choice (confirm on approve)

**A (recommended):** `backup.conf` preferred + `.env` fallback + env override; default **10**.  
**B:** Only `.env` / env (no separate file).

Approve with A or B (or tweaks), then implement.
