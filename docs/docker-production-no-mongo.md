# Docker — production without MongoDB container

Run **backend + nginx frontend** in Docker **without** starting the `mongodb` container.

Use this when:

- You already have MongoDB elsewhere (Atlas, another VM, host install)
- You only need core copying for now (SQLite) and can skip log DB

Full stack **with** Mongo in Docker: [docker-production.md](docker-production.md).

This guide uses the overlay file `docker-compose.no-mongo.yml`.

---

## Quick start

```bash
# 0) Clone (public)
sudo apt-get update && sudo apt-get install -y git
git clone https://github.com/sammirzagharcheh/PyTelegramClientCopier.git
cd PyTelegramClientCopier

# Private: git clone git@github.com:OWNER/REPO.git && cd REPO
# Full private-repo guide: docs/git-clone-and-private-repo.md

# 1) Env
cp docker.env.example docker.env
nano docker.env
# Set API_ID, API_HASH, JWT_SECRET
# Optional: point MONGO_URI at an external Mongo (see below)
# Or leave default — app starts even if Mongo is unreachable

# 2) Start (no Mongo container)
docker compose -f docker-compose.yml -f docker-compose.no-mongo.yml up --build -d

# 3) Admin
docker compose -f docker-compose.yml -f docker-compose.no-mongo.yml exec backend \
  tg-copier db create-admin you@example.com 'YourStrongPassword'

# 4) Open
# Panel:    http://localhost   (or http://SERVER_IP)
# Health:   http://localhost/health
# API docs: http://localhost/api/docs
```

Stop:

```bash
docker compose -f docker-compose.yml -f docker-compose.no-mongo.yml down
```

---

## What still runs / what changes

| Component | This mode |
|-----------|-----------|
| `backend` | Yes |
| `frontend-proxy` (nginx) | Yes |
| `mongodb` container | **No** |
| SQLite / sessions / media (`app_data` → `/app/data`) | Yes — same named volume as full production; SQLite is the primary app DB |
| Message / worker / webhook logs UI | Needs **external** Mongo, or stays empty / warns |

Core Telegram copying does **not** require Mongo. Mongo is for logs and some stats.

**Where files live:** backend mounts volume `…_app_data` at `/app/data` (`SQLITE_PATH=/app/data/app.db`, `SESSIONS_DIR`, `MEDIA_ASSETS_DIR`). There is **no** `mongo_data` volume in this mode. Multi-env GHCR deploys use per-env volumes or bind mounts — [Data volumes](docker-multi-env.md#data-volumes-sqlite-sessions-media-mongodb).

---

## Step-by-step

### Step 0 — Requirements

- Docker Engine + Compose plugin
- Git installed
- `API_ID` / `API_HASH` from [my.telegram.org](https://my.telegram.org)
- For a **private** repo: SSH deploy key or PAT ([git-clone-and-private-repo.md](git-clone-and-private-repo.md))

### Step 1 — Clone the repository

```bash
sudo apt-get update && sudo apt-get install -y git

# Public
git clone https://github.com/sammirzagharcheh/PyTelegramClientCopier.git
cd PyTelegramClientCopier

# Private SSH
# git clone git@github.com:OWNER/REPO.git && cd REPO
```

Verify:

```bash
ls docker-compose.yml docker-compose.no-mongo.yml docker.env.example
```

### Step 2 — Create `docker.env`

```bash
cp docker.env.example docker.env
nano docker.env
```

**Required:**

```env
API_ID=12345678
API_HASH=your_api_hash_here
JWT_SECRET=paste_a_long_random_secret
```

```bash
openssl rand -hex 32
```

**Paths inside the container (keep as-is):**

```env
SQLITE_PATH=/app/data/app.db
SESSIONS_DIR=/app/data/sessions
MEDIA_ASSETS_DIR=/app/data/media_assets
LOG_LEVEL=INFO
TESTING=0
```

### Step 3 — Choose Mongo strategy

#### A) No Mongo at all (simplest)

Leave or comment Mongo vars. App starts; index creation is skipped with a warning. Log pages / some stats will not work until you add Mongo later.

```env
# MONGO_URI=
# MONGO_DB=telegram_copier
```

(If unset, code defaults to `mongodb://localhost:27017`, which will fail quietly for indexes — that is OK.)

#### B) External MongoDB (recommended if you want logs)

Set URI to your real server. Examples:

```env
# Mongo on the same Linux host (outside Docker)
MONGO_URI=mongodb://host.docker.internal:27017
MONGO_DB=telegram_copier

# Mongo on another machine / Atlas
# MONGO_URI=mongodb://USER:PASSWORD@mongo.example.com:27017
# MONGO_URI=mongodb+srv://USER:PASSWORD@cluster.mongodb.net/?retryWrites=true&w=majority
MONGO_DB=telegram_copier
```

Notes:

- The overlay adds `host.docker.internal` → host gateway so **host-installed Mongo** is reachable from the backend container.
- If Mongo listens only on `127.0.0.1`, bind it to `0.0.0.0` **or** use a firewall-safe bind and allow Docker’s bridge — or run Mongo in its own container on a shared network.
- For Atlas / remote Mongo, open network access for your server IP.

Test from the backend container after start:

```bash
docker compose -f docker-compose.yml -f docker-compose.no-mongo.yml exec backend \
  tg-copier db test-mongo
```

### Step 4 — Start the stack

```bash
docker compose -f docker-compose.yml -f docker-compose.no-mongo.yml up --build -d
docker compose -f docker-compose.yml -f docker-compose.no-mongo.yml ps
```

You should see **`backend`** and **`frontend-proxy`** only (no `mongodb`).

```bash
curl -s http://localhost/health
# {"status":"ok"}
```

### Step 5 — Create admin and use the app

```bash
docker compose -f docker-compose.yml -f docker-compose.no-mongo.yml exec backend \
  tg-copier db create-admin you@example.com 'YourStrongPassword'
```

Open `http://SERVER_IP` → log in → add accounts → mappings → start workers.

---

## Shortcut: compose alias

```bash
export COMPOSE='docker compose -f docker-compose.yml -f docker-compose.no-mongo.yml'

$COMPOSE up --build -d
$COMPOSE logs -f backend
$COMPOSE exec backend tg-copier db show-config
$COMPOSE down
```

---

## Update

```bash
git pull
docker compose -f docker-compose.yml -f docker-compose.no-mongo.yml down
docker compose -f docker-compose.yml -f docker-compose.no-mongo.yml up --build -d
```

---

## Useful commands

| Task | Command |
|------|---------|
| Status | `docker compose -f docker-compose.yml -f docker-compose.no-mongo.yml ps` |
| Backend logs | `… logs -f backend` |
| Frontend logs | `… logs -f frontend-proxy` |
| Shell | `… exec backend sh` |
| Test Mongo | `… exec backend tg-copier db test-mongo` |
| Stop (keep data) | `… down` |
| Wipe app volume | `… down -v` ⚠️ deletes SQLite/sessions |

Only **`app_data`** (Compose project prefix + `_app_data`) is used here — it holds SQLite `app.db`, Telethon sessions, and media assets under `/app/data`. There is no `mongo_data` volume from this stack (external Mongo owns its own storage).

`down` keeps the app volume; `down -v` deletes SQLite/sessions/media for this project.
---

## Production checklist

- [ ] Strong `JWT_SECRET`
- [ ] Never commit `docker.env`
- [ ] If using external Mongo: TLS/auth, restricted network, backups
- [ ] Prefer HTTPS in front of port 80
- [ ] Do not publish backend `:8000` publicly unless needed
- [ ] Backup `app_data` volume regularly

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Compose still starts Mongo | Confirm **both** `-f` files; overlay sets Mongo to profile `with-mongo` |
| `depends_on` / Mongo health errors | Use `docker-compose.no-mongo.yml` (resets backend `depends_on`) |
| Cannot reach host Mongo | Use `host.docker.internal`; ensure `mongod` accepts connections from Docker bridge |
| Logs empty in UI | Set a working `MONGO_URI` and re-check with `tg-copier db test-mongo` |
| Want Mongo container later | Use plain [docker-production.md](docker-production.md) (`docker compose up` without the no-mongo overlay) |

---

## Related docs

- [Git clone & private GitHub repos](git-clone-and-private-repo.md)
- [Docker — production (with Mongo container)](docker-production.md)
- [Docker — development](docker-development.md)
- [Deploy on Ubuntu (native)](deploy-ubuntu.md)
- [Worker troubleshooting](WORKER_TROUBLESHOOTING.md)
