# Docker — multi-environment deploy (dev / tst / uat / prod)

Deploy the **same GHCR images** to isolated stacks. Each environment has:

- Its own **compose overlay** (ports / exposure)
- Its own **env file** (`EnvironmentFile`-style config for the backend container)
- Its own **Compose project name** (`tgc-dev`, `tgc-tst`, …) so volumes and containers never clash

Images are produced by CI/CD — see [GitHub Actions CI/CD](github-actions-ci-cd.md).  
For a single local production-like build from source, see [Docker — production](docker-production.md).

---

## Layout

```text
deploy/
  compose/
    docker-compose.yml              # GHCR images (no local build)
    docker-compose.dev.yml
    docker-compose.tst.yml
    docker-compose.uat.yml
    docker-compose.prod.yml
    docker-compose.no-mongo.yml     # optional: no Mongo container
    docker-compose.bind-mounts.yml  # optional: host folders for DB/session files
  env/
    docker.env.dev.example          # templates (committed)
    docker.env.tst.example
    docker.env.uat.example
    docker.env.prod.example
    docker.env.dev                  # real secrets (gitignored)
    docker.env.tst
    docker.env.uat
    docker.env.prod
  scripts/
    deploy-env.sh                   # pull + up for one env
```

---

## One-time setup per environment

```bash
cd /path/to/PyTelegramClientCopier

cp deploy/env/docker.env.dev.example  deploy/env/docker.env.dev
cp deploy/env/docker.env.tst.example  deploy/env/docker.env.tst
cp deploy/env/docker.env.uat.example  deploy/env/docker.env.uat
cp deploy/env/docker.env.prod.example deploy/env/docker.env.prod
```

Edit each file and set at least:

| Variable | Notes |
|----------|--------|
| `API_ID` / `API_HASH` | From [my.telegram.org](https://my.telegram.org) |
| `JWT_SECRET` | **Different** strong secret per env (`openssl rand -hex 32`) |
| `MONGO_DB` | Defaults already differ (`telegram_copier_dev`, `_tst`, …) — logical DB name inside Mongo |
| `LOG_LEVEL` | `DEBUG` (dev) → `WARNING` (prod) |
| `MONGO_URI` | Keep `mongodb://mongodb:27017` with in-compose Mongo; or Atlas / external URI with `NO_MONGO=1` |
| `SQLITE_PATH` / `SESSIONS_DIR` / `MEDIA_ASSETS_DIR` | Keep defaults under `/app/data/…` so the `app_data` (or bind) mount persists them — see [Data volumes](#data-volumes-sqlite-sessions-media-mongodb) |

---

## Deploy / update

```bash
chmod +x deploy/scripts/deploy-env.sh

# Pull :latest (or IMAGE_TAG) and start
./deploy/scripts/deploy-env.sh dev
./deploy/scripts/deploy-env.sh tst
./deploy/scripts/deploy-env.sh uat
./deploy/scripts/deploy-env.sh prod

# Pin a release or CI SHA
./deploy/scripts/deploy-env.sh uat v1.2.3
./deploy/scripts/deploy-env.sh prod sha-a1b2c3d
```

Optional environment variables:

| Variable | Meaning |
|----------|---------|
| `IMAGE_TAG` | Tag if not passed as 2nd argument (default `latest`) |
| `BACKEND_IMAGE` | Full image ref (override default; unified SPA + API image) |
| `GHCR_OWNER_REPO` | Override `owner/repo` used in default image names |
| `NO_MONGO=1` | Apply `docker-compose.no-mongo.yml` |
| `BIND_MOUNTS=1` | Store SQLite/sessions/media + Mongo on host paths (see [Data volumes](#data-volumes-sqlite-sessions-media-mongodb)) |
| `HOST_DATA_ROOT` | Root for bind mounts (default: `<repo>/data/docker-envs`) |
| `SKIP_PULL=1` | Do not `docker compose pull` (use local images; sets `PULL_POLICY=missing`) |

Windows PowerShell equivalent: `deploy/scripts/deploy-env.ps1` (supports `-LocalBuild`, `-BindMounts`, `-SkipPull`). See [Test on a developer machine](#test-on-a-developer-machine-local-images).

---

## Data volumes (SQLite, sessions, media, MongoDB)

Each environment keeps **its own** database and session files. Stacks never share SQLite or Mongo data, because Compose project names differ (`tgc-dev`, `tgc-tst`, `tgc-uat`, `tgc-prod`).

### What lives where (inside the backend / Mongo containers)

These paths are set in every `deploy/env/docker.env.<env>` (and must stay under `/app/data` so the volume mount covers them):

| Kind | Env vars | Path **inside** container | Purpose |
|------|----------|---------------------------|---------|
| **SQLite** (primary app DB) | `SQLITE_PATH` | `/app/data/app.db` | Users, accounts, mappings, filters, schedules, auth |
| **Telethon sessions** | `SESSIONS_DIR` | `/app/data/sessions/` | Logged-in Telegram client session files |
| **Media assets** | `MEDIA_ASSETS_DIR` | `/app/data/media_assets/` | Uploaded/transform media used by workers |
| **MongoDB** | `MONGO_URI` / `MONGO_DB` | Mongo container `/data/db` | Message / worker / webhook logs (optional if `NO_MONGO=1`) |

The unified `backend` image serves the SPA from `/app/frontend_dist` (no separate frontend container or volume).

### Default mode: Docker named volumes on the host

`deploy/compose/docker-compose.yml` mounts:

```yaml
backend:
  volumes:
    - app_data:/app/data      # SQLite + sessions + media
mongodb:
  volumes:
    - mongo_data:/data/db    # MongoDB engine files
```

Compose prefixes volume names with the **project** (`-p tgc-<env>`), so on the Docker host you get **separate** volumes per environment:

| Env | SQLite / sessions / media volume | MongoDB volume |
|-----|----------------------------------|----------------|
| **dev** | `tgc-dev_app_data` | `tgc-dev_mongo_data` |
| **tst** | `tgc-tst_app_data` | `tgc-tst_mongo_data` |
| **uat** | `tgc-uat_app_data` | `tgc-uat_mongo_data` |
| **prod** | `tgc-prod_app_data` | `tgc-prod_mongo_data` |

List them:

```bash
docker volume ls | grep tgc-
docker volume inspect tgc-uat_app_data
```

Docker stores named-volume files under the engine data root (Linux typically `/var/lib/docker/volumes/<name>/_data`). You normally **do not** edit those paths by hand; use `docker compose exec` or backups (below).

**Important:** `docker compose … down` **keeps** volumes. `down -v` **deletes** that env’s SQLite, sessions, media, and Mongo data.

Also keep `MONGO_DB` different per env (`telegram_copier_dev`, `_tst`, …) so log collections stay logically separate even if you ever pointed two stacks at one Mongo (not recommended).

### Optional mode: bind mounts on the host (visible folders per env)

If you want plain directories on the host (easier to browse/backup with `rsync`/`tar`):

```bash
BIND_MOUNTS=1 ./deploy/scripts/deploy-env.sh uat

# Custom root (recommended on servers):
BIND_MOUNTS=1 HOST_DATA_ROOT=/var/lib/telegram-copier ./deploy/scripts/deploy-env.sh prod
```

This applies `deploy/compose/docker-compose.bind-mounts.yml` and creates:

```text
<HOST_DATA_ROOT>/<env>/app/app.db
<HOST_DATA_ROOT>/<env>/app/sessions/
<HOST_DATA_ROOT>/<env>/app/media_assets/
<HOST_DATA_ROOT>/<env>/mongo/          # MongoDB files (skip when NO_MONGO=1)
```

Example with defaults (`HOST_DATA_ROOT=<repo>/data/docker-envs`):

```text
data/docker-envs/dev/app/…
data/docker-envs/tst/app/…
data/docker-envs/uat/app/…
data/docker-envs/prod/app/…
```

(`data/` is gitignored.)

Do **not** point two environments at the same host folder. Do **not** change `SQLITE_PATH` / `SESSIONS_DIR` / `MEDIA_ASSETS_DIR` to paths outside `/app/data` unless you also change the mount.

### Inspect / backup one environment

**Named volumes (default):**

```bash
# SQLite + sessions + media
docker run --rm -v tgc-uat_app_data:/data -v "$(pwd):/backup" alpine \
  tar czf /backup/tgc-uat-app_data.tgz -C /data .

# Mongo
docker run --rm -v tgc-uat_mongo_data:/data -v "$(pwd):/backup" alpine \
  tar czf /backup/tgc-uat-mongo_data.tgz -C /data .
```

**Bind mounts:**

```bash
sudo tar czf tgc-uat-app.tgz -C /var/lib/telegram-copier/uat app
sudo tar czf tgc-uat-mongo.tgz -C /var/lib/telegram-copier/uat mongo
```

**Peek at SQLite inside a running stack:**

```bash
docker compose -p tgc-uat \
  -f deploy/compose/docker-compose.yml \
  -f deploy/compose/docker-compose.uat.yml \
  --env-file deploy/env/docker.env.uat \
  exec backend ls -la /app/data
```

### Root `docker compose` (single stack) vs multi-env

| Mode | Project (typical) | App volume | Mongo volume |
|------|-------------------|------------|--------------|
| Root [docker-production.md](docker-production.md) | directory name, e.g. `telegramclientcopier` | `…_app_data` | `…_mongo_data` |
| Multi-env `tgc-<env>` | `tgc-dev` … `tgc-prod` | `tgc-<env>_app_data` | `tgc-<env>_mongo_data` |

These are **different** volumes. Running both on one host does not share SQLite; they only conflict on **ports** (especially `:80`).

---

## Ports

| Env | Panel (SPA + `/api`) | API alias | MongoDB |
|-----|----------------------|-----------|---------|
| **dev** | `8080` | `8001` | `27018` |
| **tst** | `8081` | `8002` | `27019` |
| **uat** | `8082` | `8003` | `27020` |
| **prod** | `80` | not published | not published |

You can run **dev + tst + uat** on one host at the same time. Prefer a dedicated host (or firewall) for **prod**.

---

## Test on a developer machine (local images)

Use this before relying on GHCR. On Windows, prefer the PowerShell helper (Docker Desktop); on Linux/macOS use the bash script.

### 1) Create the env file

```bash
cp deploy/env/docker.env.dev.example deploy/env/docker.env.dev
# Fill API_ID, API_HASH, JWT_SECRET (can copy from your local docker.env)
```

PowerShell:

```powershell
Copy-Item deploy\env\docker.env.dev.example deploy\env\docker.env.dev
# edit deploy\env\docker.env.dev
```

### 2) Build + deploy `dev` with visible host data folders

**Windows (PowerShell):**

```powershell
.\deploy\scripts\deploy-env.ps1 -Environment dev -LocalBuild -BindMounts
```

**Linux / macOS / Git Bash:**

```bash
docker build -f Dockerfile.backend -t local/tgc-backend:dev .
SKIP_PULL=1 BIND_MOUNTS=1 \
  BACKEND_IMAGE=local/tgc-backend:dev \
  ./deploy/scripts/deploy-env.sh dev
```

### 3) Verify

| Check | Expect |
|-------|--------|
| Panel | http://localhost:8080 |
| API health (alias) | http://localhost:8001/health → `{"status":"ok"}` |
| Panel health | http://localhost:8080/health → `{"status":"ok"}` |
| SQLite on host (bind mounts) | `data/docker-envs/dev/app/app.db` |
| Mongo on host (bind mounts) | `data/docker-envs/dev/mongo/` |

Create admin + login smoke:

```powershell
docker compose -p tgc-dev `
  -f deploy/compose/docker-compose.yml `
  -f deploy/compose/docker-compose.dev.yml `
  -f deploy/compose/docker-compose.bind-mounts.yml `
  --env-file deploy/env/docker.env.dev `
  exec backend tg-copier db create-admin you@example.com 'YourStrongPassword'
```

Open http://localhost:8080 and sign in.

### 4) Stop (keep data)

```powershell
docker compose -p tgc-dev `
  -f deploy/compose/docker-compose.yml `
  -f deploy/compose/docker-compose.dev.yml `
  -f deploy/compose/docker-compose.bind-mounts.yml `
  --env-file deploy/env/docker.env.dev `
  down
```

Bind-mount folders under `data/docker-envs/dev/` remain. Delete that folder only if you want a wipe.

---

## Useful Compose commands

Replace `uat` with your env; project is always `tgc-<env>`:

```bash
ENV=uat
PROJECT=tgc-$ENV
FILES="-f deploy/compose/docker-compose.yml -f deploy/compose/docker-compose.$ENV.yml"
ENVFILE="deploy/env/docker.env.$ENV"

docker compose -p "$PROJECT" $FILES --env-file "$ENVFILE" ps
docker compose -p "$PROJECT" $FILES --env-file "$ENVFILE" logs -f backend
docker compose -p "$PROJECT" $FILES --env-file "$ENVFILE" exec backend tg-copier db create-admin admin@example.com 'Secret'
docker compose -p "$PROJECT" $FILES --env-file "$ENVFILE" pull
docker compose -p "$PROJECT" $FILES --env-file "$ENVFILE" up -d
docker compose -p "$PROJECT" $FILES --env-file "$ENVFILE" down
```

`down` does **not** delete named volumes (or host bind-mount folders). To wipe **named-volume** data for one env:

```bash
docker compose -p tgc-uat $FILES --env-file "$ENVFILE" down -v
```

To wipe **bind-mount** data, stop the stack then delete that env’s host folder (e.g. `rm -rf /var/lib/telegram-copier/uat`).
---

## How this maps to “EnvironmentFile”

On systemd installs, Ubuntu docs use an `EnvironmentFile=` pointing at `.env`.  
In Docker multi-env deploys, the equivalent is:

```text
deploy/env/docker.env.<env>  →  backend service env_file in docker-compose.<env>.yml
```

Compose injects those variables into the backend container the same way systemd would inject an EnvironmentFile into a unit.

---

## Same host as local `docker compose` (root)

Root `docker-compose.yml` uses project name from the directory (often `telegramclientcopier`) and ports **80 / 8000 / 27017**.

Multi-env stacks use `tgc-*` and alternate ports (except prod `:80`).  
**Do not** run root prod-like compose and `tgc-prod` together on the same host without changing ports — both want host port 80.

---

## Checklist

- [ ] GHCR image exists (`backend` — unified SPA + API; legacy `frontend` packages are obsolete)
- [ ] `docker login ghcr.io` on the host (if private packages)
- [ ] Real `deploy/env/docker.env.<env>` created from examples
- [ ] Unique `JWT_SECRET` / `MONGO_DB` per env
- [ ] Understand data location: named volumes `tgc-<env>_app_data` / `_mongo_data`, or bind mounts under `HOST_DATA_ROOT/<env>/`
- [ ] `./deploy/scripts/deploy-env.sh <env>` succeeds
- [ ] Admin user created
- [ ] Panel opens on the env’s HTTP port
- [ ] `/health` OK (panel port or API alias on non-prod)
- [ ] Backup plan for SQLite (`app.db`), sessions, and Mongo per env
---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `Missing env file` | Copy the matching `*.example` to `docker.env.<env>` |
| Image pull denied | GHCR login + package permissions |
| Port is already allocated | Stop conflicting compose project or edit the overlay |
| App uses wrong DB/secret | Confirm the overlay’s `env_file` path and file contents |
| Workers / sessions lost after recreate | Normal if you used `down -v` (named volumes) or deleted the bind-mount folder; otherwise data is in `tgc-<env>_app_data` or `HOST_DATA_ROOT/<env>/app` |
| Cannot find `app.db` on the host | Default is a **named volume**, not a file in the git repo — use `docker volume inspect tgc-<env>_app_data` or enable `BIND_MOUNTS=1` |
| Two envs share users/sessions | They must not share the same volume/bind path; use different `-p tgc-<env>` (script default) |
