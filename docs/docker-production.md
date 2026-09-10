# Docker — production (production-like)

Run the full stack in containers: **MongoDB + backend API + nginx frontend**.

Use this for:

- Local “production-like” testing
- Deploying on a Linux server with Docker Engine

Need **no MongoDB container** (external Mongo or SQLite-only)? Use [Docker — production without Mongo](docker-production-no-mongo.md).

For coding with live reload, use [Docker — development](docker-development.md) instead.

---

## Quick start

```bash
# 0) Clone (public)
sudo apt-get update && sudo apt-get install -y git
git clone https://github.com/sammirzagharcheh/PyTelegramClientCopier.git
cd PyTelegramClientCopier

# Private repo (SSH) — see docs/git-clone-and-private-repo.md
# git clone git@github.com:OWNER/REPO.git && cd REPO

# 1) Env file
cp docker.env.example docker.env
nano docker.env
# Fill API_ID, API_HASH, and a strong JWT_SECRET

# 2) Start
docker compose up --build -d

# 3) Admin user
docker compose exec backend tg-copier db create-admin you@example.com 'YourStrongPassword'

# 4) Open
# Panel:     http://localhost   (or http://SERVER_IP)
# API docs:  http://localhost/api/docs
# Health:    http://localhost/health
```

Stop:

```bash
docker compose down
```

---

## Step-by-step

### Step 0 — Requirements

On the host (Ubuntu 22.04+ example):

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
# Install Docker Engine + Compose plugin from Docker’s official docs:
# https://docs.docker.com/engine/install/ubuntu/
docker --version
docker compose version
```

Get Telegram credentials from [my.telegram.org](https://my.telegram.org).

### Step 1 — Clone the repository

**Public:**

```bash
git clone https://github.com/sammirzagharcheh/PyTelegramClientCopier.git
cd PyTelegramClientCopier
```

**Private (recommended: SSH deploy key):**

```bash
# After adding a deploy key — full steps: docs/git-clone-and-private-repo.md
git clone git@github.com:OWNER/REPO.git
cd REPO
```

**Private (HTTPS + PAT):**

```bash
git clone https://github.com/OWNER/REPO.git
# Username = GitHub user, Password = personal access token (not account password)
cd REPO
```

Verify you are in the project root:

```bash
ls docker-compose.yml docker.env.example Dockerfile.backend
```

### Step 2 — Create `docker.env`

```bash
cp docker.env.example docker.env
nano docker.env
```

Required:

```env
API_ID=12345678
API_HASH=your_api_hash_here
JWT_SECRET=change-me-in-production
```

Generate a secret:

```bash
openssl rand -hex 32
```

Defaults already set for Docker networking:

```env
MONGO_URI=mongodb://mongodb:27017
MONGO_DB=telegram_copier
SQLITE_PATH=/app/data/app.db
SESSIONS_DIR=/app/data/sessions
MEDIA_ASSETS_DIR=/app/data/media_assets
LOG_LEVEL=INFO
TESTING=0
```

Do **not** commit `docker.env` (it is gitignored).

### Step 3 — Build and start

```bash
docker compose up --build -d
```

Services started:

| Service | Role | Host port |
|---------|------|-----------|
| `mongodb` | Logs database | `27017` |
| `backend` | FastAPI + workers | `8000` |
| `frontend-proxy` | nginx SPA + `/api` proxy | `80` |

Check:

```bash
docker compose ps
curl -s http://localhost/health
# {"status":"ok"}
```

### Step 4 — Create the first admin

DB init runs automatically when the backend container starts. Create an admin once:

```bash
docker compose exec backend tg-copier db create-admin you@example.com 'YourStrongPassword'
```

### Step 5 — Use the app

1. Open `http://SERVER_IP` (or `http://localhost`)
2. Log in
3. Add Telegram accounts → mappings → start workers

---

## Deploy on an Ubuntu server with Docker

Same steps as above on the VPS. Extra hardening tips:

### Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp   # if you terminate TLS on the host
# Prefer NOT exposing 27017 / 8000 publicly in real production
sudo ufw enable
```

For a stricter compose setup later, remove or bind host ports:

- Keep only port `80` (and `443`) public
- Leave `8000` and `27017` off the public interface (internal Docker network only)

### HTTPS (recommended for public VPS)

Simplest pattern: put **host nginx or Caddy** in front of Docker’s port 80, or use a reverse proxy container (Traefik / Caddy) with Let’s Encrypt.

Example with host nginx reverse-proxying to `127.0.0.1:80`, then:

```bash
sudo certbot --nginx -d copier.example.com
```

### Data persistence

Named volumes (survive `docker compose down`):

| Volume | Contents |
|--------|----------|
| `mongo_data` | MongoDB files |
| `app_data` | SQLite DB, Telethon sessions, media assets, worker logs |

Backup example:

```bash
docker compose stop backend
docker run --rm -v telegramclientcopier_app_data:/data -v "$(pwd):/backup" alpine \
  tar czf /backup/app_data-backup.tgz -C /data .
docker compose start backend
```

(Volume name may differ; check with `docker volume ls`.)

---

## Update to latest code

```bash
git pull
docker compose down
docker compose up --build -d
docker compose logs -f backend
```

---

## Useful commands

| Task | Command |
|------|---------|
| Status | `docker compose ps` |
| Backend logs | `docker compose logs -f backend` |
| Frontend logs | `docker compose logs -f frontend-proxy` |
| Mongo logs | `docker compose logs -f mongodb` |
| Shell in backend | `docker compose exec backend sh` |
| Show config | `docker compose exec backend tg-copier db show-config` |
| Test Mongo | `docker compose exec backend tg-copier db test-mongo` |
| Restart stack | `docker compose restart` |
| Stop (keep data) | `docker compose down` |
| Stop + **delete volumes** | `docker compose down -v` ⚠️ destroys DB/sessions |

---

## Production checklist

- [ ] Strong `JWT_SECRET` in `docker.env`
- [ ] `API_ID` / `API_HASH` private; never commit `docker.env`
- [ ] Prefer HTTPS in front of the stack
- [ ] Do not expose Mongo (`27017`) or raw API (`8000`) to the internet
- [ ] Backup `app_data` and `mongo_data` volumes
- [ ] `TESTING=0` in production

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Port 80 / 8000 / 27017 in use | Stop the other process, or change host ports in `docker-compose.yml` |
| Backend unhealthy / Mongo not ready | Wait ~30s; `docker compose logs -f mongodb backend` |
| Blank page / API errors | Use `http://localhost` (or your server IP), not a mismatched hostname |
| Need clean reset | `docker compose down -v` then `up --build -d` (destructive) |
| Workers / sessions | See [WORKER_TROUBLESHOOTING.md](WORKER_TROUBLESHOOTING.md) |

Podman works with the same files:

```bash
podman compose up --build -d
```

---

## Related docs

- [Git clone & private GitHub repos](git-clone-and-private-repo.md)
- [Docker — production without Mongo](docker-production-no-mongo.md)
- [Docker — development](docker-development.md) (hot reload)
- [Deploy on Ubuntu (native)](deploy-ubuntu.md)
- [Worker troubleshooting](WORKER_TROUBLESHOOTING.md)
