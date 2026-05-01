# Database Migration Runbook

Comprehensive, environment-specific database migration procedures for this project.

This runbook covers:

- Windows (PowerShell)
- Ubuntu Linux (systemd-based deployment)
- Docker / Docker Compose

It assumes PostgreSQL is the runtime database and Alembic migrations are used for schema upgrades.

---

## 1) Core Principles (All Environments)

1. **Backup first** (always).
2. **Run DB migration before app rollout** (for this project's migration flow).
3. **Deploy app update after successful migration**.
4. **Smoke test immediately** after deploy.
5. **Monitor and be ready to rollback**.

Recommended rollout order:

1. Development
2. Test / staging
3. Production

---

## 2) Standard Migration Commands

The project includes helper scripts:

- Windows: `scripts/migrate.ps1`
- Linux/macOS/bash: `scripts/migrate.sh`

Supported actions:

- `upgrade`
- `downgrade`
- `current`
- `history`

Supported environments:

- `dev` -> `telegram_copier_dev`
- `test` -> `telegram_copier_test`
- `prod` -> `telegram_copier_prod`

---

## 2.5) SQLite → PostgreSQL data import (one-time)

**Alembic** applies **schema** only (tables, indexes, `alembic_version`). To copy **application rows** from an existing SQLite file (`data/app.db` or another path) into PostgreSQL, use:

- `scripts/migrate_sqlite_to_postgres.py`

### What it does

1. **Truncates** a fixed list of tables in PostgreSQL (`users`, `channel_mappings`, `dest_message_index`, etc.—see the script).
2. **Bulk-copies** rows from the SQLite file into those tables in dependency order.
3. **Resets** PostgreSQL serial sequences for tables that use `id` sequences.

### Critical warnings

- **Backup PostgreSQL first** (`pg_dump` / your provider snapshot). This script **destroys existing data** in those tables before import.
- **Production cutover:** run **after** `alembic upgrade head` so the Postgres schema matches what the script expects.
- **DSN for this script** must be a plain **`postgresql://`** URL (used by `asyncpg.connect`), **not** `postgresql+asyncpg://` (that form is for SQLAlchemy in the app).
- **PgBouncer:** imports have succeeded on `host:6432` in practice; if `TRUNCATE` / `COPY` fails, use a **session-mode** pool or connect to PostgreSQL **directly** on port **5432** for the import only.

### Example (VPS, paths as deployed)

Run as the app user from the install directory:

```bash
cd /opt/telegram-copier
sudo -u tgcopier bash -lc '
  cd /opt/telegram-copier && .venv/bin/python scripts/migrate_sqlite_to_postgres.py \
    --sqlite-path /opt/telegram-copier/data/app.db \
    --postgres-dsn "postgresql://<user>:<password>@<host>:<port>/<database>"
'
sudo systemctl restart telegram-copier
curl -fsS http://127.0.0.1:8000/health
```

Replace `<user>`, `<password>`, `<host>`, `<port>`, and `<database>` with your values. URL-encode special characters in the password if needed.

### After import

- Ensure **`DB_BACKEND=postgres`** and **`DATABASE_URL`** (with `postgresql+asyncpg://...`) point at the same database the app should use.
- Keep or archive the SQLite file according to your retention policy; the runtime should use Postgres only.

---

## 2.6) End-to-end production cutover (ordered checklist)

Use this when moving an existing deployment from SQLite to PostgreSQL (schema + optional row import). Check items off as you go.

1. [ ] **Backup** PostgreSQL (`pg_dump` or provider snapshot) before any destructive step.
2. [ ] **Deploy code** that includes Alembic migrations and PgBouncer-safe settings (`alembic/env.py` uses `statement_cache_size=0` / `prepared_statement_cache_size=0` for asyncpg through poolers; `src/app/db/postgres.py` matches for the running API).
3. [ ] **Configure `.env` on the server:** `DB_BACKEND=postgres` and `DATABASE_URL=postgresql+asyncpg://...` pointing at the correct database (same DB you will migrate into).
4. [ ] **Apply schema:** `alembic upgrade head` (as the app user, from the install dir, with env loaded so `DATABASE_URL` is set).
5. [ ] **Optional — import SQLite rows:** run `scripts/migrate_sqlite_to_postgres.py` only if you need historical data (see § 2.5). Skip if this is a fresh database with no SQLite source.
6. [ ] **Restart** `telegram-copier` (`systemctl restart telegram-copier`; use `restart`, not `reload`, unless you add `ExecReload` to the unit).
7. [ ] **Smoke test:** `curl http://127.0.0.1:8000/health`, then log in and hit one read and one write API path you care about.
8. [ ] **Monitor:** `journalctl -u telegram-copier -f` briefly after cutover.

---

## 3) Pre-Migration Checklist

Complete this checklist before every migration:

- [ ] Confirm branch/tag/commit that will be deployed.
- [ ] Review migration files in `alembic/versions`.
- [ ] Check for risky operations (type rewrites, heavy index creation, table locks).
- [ ] Confirm DB credentials and connectivity.
- [ ] Confirm migration scripts exist on target host.
- [ ] Announce maintenance window if needed.
- [ ] Take a fresh backup and verify backup file exists.
- [ ] Confirm rollback plan and owner.

---

## 4) Windows Runbook (PowerShell)

### 4.1 Pre-check

From repo root:

```powershell
git pull
git status
```

Set DB password in current shell:

```powershell
$env:PGPASSWORD = "<postgres-password>"
```

Check current migration state:

```powershell
./scripts/migrate.ps1 -Environment prod -Action current
./scripts/migrate.ps1 -Environment prod -Action history
```

### 4.2 Backup

Example using `pg_dump`:

```powershell
pg_dump -h <db-host> -p 5432 -U <db-user> -d telegram_copier_prod -Fc -f "D:\backups\telegram_copier_prod_$(Get-Date -Format 'yyyyMMdd_HHmm').dump"
```

### 4.3 Run migration

```powershell
./scripts/migrate.ps1 -Environment prod -Action upgrade -Revision head
./scripts/migrate.ps1 -Environment prod -Action current
```

### 4.4 Deploy app update

Use your normal deploy path (service restart / process manager / release pipeline).

### 4.5 Smoke test

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health"
```

Then verify:

- login endpoint
- one read endpoint
- one write endpoint
- worker start/stop flow

### 4.6 Rollback

App rollback only (preferred when DB migration is backward-compatible):

- redeploy previous app version

DB rollback:

```powershell
./scripts/migrate.ps1 -Environment prod -Action downgrade -Revision -1
```

Or restore backup:

```powershell
pg_restore -h <db-host> -p 5432 -U <db-user> -d telegram_copier_prod -c "D:\backups\<backup-file>.dump"
```

---

## 5) Ubuntu Linux Runbook (systemd)

### 5.1 SSH and pre-check

```bash
ssh <user>@<host>
cd /opt/telegram-copier
git pull
git status
```

Set DB password:

```bash
export PGPASSWORD='<postgres-password>'
```

Check migration state:

```bash
./scripts/migrate.sh prod current
./scripts/migrate.sh prod history
```

### 5.2 Backup

```bash
mkdir -p /opt/telegram-copier/backups
pg_dump -h <db-host> -p 5432 -U <db-user> -d telegram_copier_prod \
  -Fc -f "/opt/telegram-copier/backups/prod_$(date +%F_%H%M).dump"
```

### 5.3 Stop app (optional but recommended for risky migrations)

```bash
sudo systemctl stop telegram-copier
```

### 5.4 Run migration

```bash
./scripts/migrate.sh prod upgrade head
./scripts/migrate.sh prod current
```

### 5.5 Start app / deploy update

```bash
sudo systemctl start telegram-copier
sudo systemctl status telegram-copier --no-pager
```

### 5.6 Smoke test

```bash
curl -fsS http://127.0.0.1:8000/health
```

Then check authenticated endpoints and one write flow.

### 5.7 Monitor

```bash
journalctl -u telegram-copier -f
```

### 5.8 Rollback

Downgrade:

```bash
./scripts/migrate.sh prod downgrade -1
```

Restore backup:

```bash
pg_restore -h <db-host> -p 5432 -U <db-user> -d telegram_copier_prod -c "/opt/telegram-copier/backups/<file>.dump"
```

---

## 6) Docker / Docker Compose Runbook

### 6.1 Identify DB container and credentials

Example container name:

- `postgres_db`

List containers:

```bash
docker ps
```

### 6.2 Backup from container

```bash
docker exec postgres_db pg_dump -U <db-user> -d telegram_copier_prod -Fc > "prod_$(date +%F_%H%M).dump"
```

### 6.3 Run migration from app container (preferred)

If backend container has project code + venv:

```bash
docker exec -e PGPASSWORD='<postgres-password>' <backend-container> \
  bash -lc "cd /app && ./scripts/migrate.sh prod upgrade head"
```

Alternative: run migration from host against DB host/port:

```bash
export PGPASSWORD='<postgres-password>'
./scripts/migrate.sh prod upgrade head
```

### 6.4 Restart app containers

```bash
docker compose up -d --build backend
```

Or full stack if needed:

```bash
docker compose up -d --build
```

### 6.5 Smoke test

```bash
curl -fsS http://localhost/health
# or
curl -fsS http://localhost:8000/health
```

### 6.6 Rollback

- redeploy previous backend image/tag
- optionally downgrade migration or restore DB dump

Restore example:

```bash
cat prod_<timestamp>.dump | docker exec -i postgres_db pg_restore -U <db-user> -d telegram_copier_prod -c
```

---

## 7) Post-Migration Verification Checklist

- [ ] `alembic current` shows expected revision.
- [ ] `/health` is OK.
- [ ] Login works.
- [ ] Key read endpoints return expected payload shape.
- [ ] At least one write workflow works end-to-end.
- [ ] Worker start/stop flows work.
- [ ] No sustained DB errors in logs.
- [ ] Error rate and latency are stable.

---

## 8) Common Failure Modes and Fixes

### `28P01` authentication failed

- check username case (e.g. `8n8user` != `8n8User`)
- verify latest password (clear client-side cached credentials)
- verify host/port/db name

### Migration script cannot connect

- ensure `PGPASSWORD` is exported in current shell/session
- verify DB host firewall/network path
- test direct connection with `psql`

### App starts but endpoints fail

- likely app code expects newer schema than current DB revision
- run `current`, confirm revision, then re-run `upgrade head`

### Long-running migration

- stop/quiet high-write traffic
- run during maintenance window
- consider splitting into multiple revisions

---

## 9) Operational Recommendations

- Keep migrations small and reversible.
- Avoid combining schema rewrite + app behavior rewrite in one release when possible.
- Prefer additive changes first (add column/table/index), cleanup in later release.
- Validate on `test` before `prod` every time.
- Keep runbook + rollback command snippets in your release ticket.
