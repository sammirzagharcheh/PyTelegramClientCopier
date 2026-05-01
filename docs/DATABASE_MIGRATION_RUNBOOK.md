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
5. **Monitor deployment health**.

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

## 2.5) PostgreSQL-only runtime note

Schema management is Alembic-first (`alembic upgrade head`).
SQLite import tooling is archived and not part of supported runtime operations.

---

## 2.6) End-to-end production cutover (ordered checklist)

Use this when deploying or upgrading PostgreSQL-backed environments. Check items off as you go.

1. [ ] **Backup** PostgreSQL (`pg_dump` or provider snapshot) before any destructive step.
2. [ ] **Deploy code** that includes Alembic migrations and PgBouncer-safe settings (`alembic/env.py` uses `statement_cache_size=0` / `prepared_statement_cache_size=0` for asyncpg through poolers; `src/app/db/postgres.py` matches for the running API).
3. [ ] **Configure `.env` on the server:** `DB_BACKEND=postgres` and `DATABASE_URL=postgresql+asyncpg://...` pointing at the correct database (same DB you will migrate into).
4. [ ] **Apply schema:** `alembic upgrade head` (as the app user, from the install dir, with env loaded so `DATABASE_URL` is set).
5. [ ] **Skip legacy SQLite import tooling:** runtime is PostgreSQL-only.
6. [ ] **Restart** `telegram-copier` (`systemctl restart telegram-copier`; use `restart`, not `reload`, unless you add `ExecReload` to the unit).
7. [ ] **Smoke test:** `curl http://127.0.0.1:8000/health`, then log in and hit one read and one write API path you care about.
8. [ ] **Monitor:** `journalctl -u telegram-copier -f` briefly after cutover.

**Login still fails (“invalid email or password”) after cutover:** deploy the latest auth fixes, then on the server (as `tgcopier`, with `.env` loading Postgres) run: `tg-copier db set-password your@email.com 'NewStrongPassword'` to replace the stored bcrypt hash (e.g. corrupted import or unknown legacy hash).

**Diagnose on the VPS:** First ensure the repo is actually updated to `main` (see below). Then: `sudo bash /opt/telegram-copier/scripts/diagnose-prod-login.sh` prints service status, `tg-copier db show-config`, and `tg-copier db inspect-auth-users` (per-user `status`, hash length, `bcrypt_ok`). If `bcrypt_ok` is false or `status` is not `active`, fix data or reset the password with `set-password`.

**Post-deploy smoke (health + login + /auth/me):**

```bash
cd /opt/telegram-copier
bash scripts/smoke-auth.sh "your@email.com" "yourPassword"
```

Optional custom API base:

```bash
API_BASE="http://127.0.0.1:8000/api" bash scripts/smoke-auth.sh "your@email.com" "yourPassword"
```

**Git “dubious ownership” / missing new files after “pull”:** The tree under `/opt/telegram-copier` is owned by the app user (`tgcopier`). Running `sudo git …` runs Git **as root**, so Git aborts and **no fetch/reset happens**—you stay on an old commit and new scripts (e.g. `scripts/diagnose-prod-login.sh`) will be missing. Prefer **`sudo bash /opt/telegram-copier/scripts/update-vps.sh`** (it runs `git` as `tgcopier`), or manually:

```bash
sudo -u tgcopier bash -lc 'cd /opt/telegram-copier && git fetch origin && git reset --hard origin/main'
```

Only if you must run `git` as root, add once: `git config --global --add safe.directory /opt/telegram-copier` (weaker than using `tgcopier` for Git).

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
- [ ] Confirm recovery plan and owner.

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

Application rollback only (code rollback):

- redeploy previous app version

DB recovery:

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
- Keep runbook + recovery command snippets in your release ticket.
