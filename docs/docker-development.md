# Docker — development (hot reload)

Run the stack in Docker with **live reload** while you edit code.

- Backend: uvicorn `--reload` + bind-mount `./src`
- Frontend: Vite on port **5173** inside a Node container
- MongoDB: same as production compose
- `frontend-proxy` (nginx) is **disabled** in this mode

For a production-like container run (built SPA on port 80), see [Docker — production](docker-production.md).

---

## Quick start

```bash
# 0) Clone (public)
sudo apt-get update && sudo apt-get install -y git   # Linux; skip if git exists
git clone https://github.com/sammirzagharcheh/PyTelegramClientCopier.git
cd PyTelegramClientCopier

# Private: git clone git@github.com:OWNER/REPO.git && cd REPO
# See docs/git-clone-and-private-repo.md

# 1) Env
cp docker.env.example docker.env
nano docker.env
# Set API_ID, API_HASH, JWT_SECRET

# 2) Start (foreground recommended while coding)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# 3) In another terminal: create admin (first time)
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend \
  tg-copier db create-admin you@example.com 'YourStrongPassword'

# 4) Open
# Frontend:  http://localhost:5173
# API docs:  http://localhost:8000/api/docs
# Health:    http://localhost:8000/health
```

Stop: `Ctrl+C`, or:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
```

---

## Step-by-step

### Step 0 — Requirements

- Docker Engine + Compose plugin
- Git
- Telegram `API_ID` / `API_HASH` from [my.telegram.org](https://my.telegram.org)
- Private repo? Set up SSH or PAT first: [git-clone-and-private-repo.md](git-clone-and-private-repo.md)

### Step 1 — Clone the repository

```bash
# Public
git clone https://github.com/sammirzagharcheh/PyTelegramClientCopier.git
cd PyTelegramClientCopier

# Private SSH
# git clone git@github.com:OWNER/REPO.git && cd REPO
```

Verify:

```bash
ls docker-compose.yml docker-compose.dev.yml frontend/package.json src/
```

### Step 2 — Configure `docker.env`

```bash
cp docker.env.example docker.env
```

Minimum:

```env
API_ID=
API_HASH=
JWT_SECRET=dev-secret-change-me
MONGO_URI=mongodb://mongodb:27017
MONGO_DB=telegram_copier
SQLITE_PATH=/app/data/app.db
SESSIONS_DIR=/app/data/sessions
MEDIA_ASSETS_DIR=/app/data/media_assets
LOG_LEVEL=INFO
TESTING=0
```

### Step 3 — Start the dev stack

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

What this overlay does (`docker-compose.dev.yml`):

| Change | Effect |
|--------|--------|
| Backend command | `init-db` + uvicorn `--reload` |
| `./src` mounted | Python code reloads on save |
| `frontend-proxy` | Disabled (`profiles: ["prodlike"]`) |
| `frontend-dev` | `npm ci` + `npm run dev` on **5173** |
| `./frontend` mounted | Vite HMR for UI changes |

### Step 4 — Create admin (once)

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend \
  tg-copier db create-admin you@example.com 'YourStrongPassword'
```

### Step 5 — Develop

- Edit files under `src/` → API reloads
- Edit files under `frontend/` → Vite refreshes
- If **frontend `package.json` / lockfile** changed, recreate so `npm ci` runs again:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

---

## Detached mode (optional)

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f backend frontend-dev
```

---

## Useful commands

Use the **same `-f` pair** on every command:

```bash
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.dev.yml"

$COMPOSE ps
$COMPOSE logs -f backend
$COMPOSE logs -f frontend-dev
$COMPOSE exec backend sh
$COMPOSE exec backend tg-copier db show-config
$COMPOSE exec backend tg-copier db test-mongo
$COMPOSE down          # keep volumes
$COMPOSE down -v       # wipe DB/sessions (destructive)
```

---

## Ports (dev)

| URL | Service |
|-----|---------|
| http://localhost:5173 | Vite frontend |
| http://localhost:8000 | Backend API |
| http://localhost:27017 | MongoDB |

Vite proxies `/api` and `/health` to the backend (`VITE_PROXY_TARGET=http://backend:8000` inside the container).

---

## Tips

- Prefer opening **http://localhost:5173**, not port 80 (nginx is off in this mode).
- SQLite + sessions persist in the `app_data` volume unless you use `down -v`.
- For a production-like check of the built UI, switch to [Docker — production](docker-production.md).
- Worker issues: [WORKER_TROUBLESHOOTING.md](WORKER_TROUBLESHOOTING.md)
- Feature → test map: [dev-cheatsheet.md](dev-cheatsheet.md)

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Frontend deps out of date | Recreate stack (`down` then `up --build`) so `npm ci` re-runs |
| Port 5173 / 8000 busy | Stop local Vite/API or change published ports in compose |
| Changes not reloading | Confirm you started with **both** compose files |
| CORS / wrong host | Use `http://localhost:5173` |

---

## Related docs

- [Git clone & private GitHub repos](git-clone-and-private-repo.md)
- [Docker — production](docker-production.md)
- [Deploy on Ubuntu (native)](deploy-ubuntu.md)
- [Developer cheat sheet](dev-cheatsheet.md)
