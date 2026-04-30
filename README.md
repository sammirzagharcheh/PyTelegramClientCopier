# Telegram Client Copier

Multi-tenant Telegram copier with admin controls, filtering, and media forwarding.

## Quick start

1. Create `.env` with:
   - `API_ID`
   - `API_HASH`
   - `JWT_SECRET` (optional, for auth; set in production)
   - `BOT_TOKEN` (optional, for live Telegram test; from @BotFather)
   - `MONGO_URI` (optional)
   - `MONGO_DB` (optional)
   - `DB_BACKEND=postgres`
   - `DATABASE_URL=postgresql+asyncpg://...`
2. Install dependencies:
   - `pip install -e .`
3. Initialize DB schema:
   - `tg-copier db init-db`
4. Create first admin:
   - `tg-copier db create-admin your@email.com yourpassword`
5. Run API server:
   - `tg-copier api`
6. Run the web panel:
   - `cd frontend && npm install && npm run dev`
7. Open <http://localhost:5173> and log in.

## Database Cutover And Rollback

- Default runtime backend is PostgreSQL (`DB_BACKEND=postgres`).
- Required for Postgres mode: `DATABASE_URL` must be set.
- Rollback path (temporary/legacy): set `DB_BACKEND=sqlite` and `SQLITE_PATH=data/app.db`, then re-run `tg-copier db init-db`.

## Environment Database Split

Use separate PostgreSQL databases per environment to avoid cross-environment data contamination:

- development: `telegram_copier_dev`
- test/CI: `telegram_copier_test`
- production: `telegram_copier_prod`

Recommended env files:

- `.env` -> dev database
- `.env.test` -> test database
- `.env.production` (or secret manager) -> production database

### DataGrip (Local PostgreSQL) Connection

When connecting DataGrip to local Docker PostgreSQL, use the same values as your local `.env`.

Field mode:

- Host: `localhost`
- Port: `5432`
- Database: `telegram_copier_dev` (or `..._test` / `..._prod`)
- User: value from `DATABASE_URL` user segment (for this project usually `8n8user`)
- Password: value from `DATABASE_URL` password segment

URL mode example:

```text
jdbc:postgresql://localhost:5432/telegram_copier_dev
```

Then set user/password in DataGrip auth fields (or append as URL params if you prefer).

Common fixes for auth error `28P01`:

- ensure username case matches exactly (e.g. `8n8user` is not `8n8User`)
- click **Change Credentials** and re-enter password (clears cached old value)
- disable SSL for local Docker unless you explicitly configured SSL

## Docker (Local, production-like)

Run frontend + backend + MongoDB in containers for local development using the latest code in this repo.

1. Create Docker env file:
   - Linux/macOS: `cp docker.env.example docker.env`
   - PowerShell: `Copy-Item docker.env.example docker.env`
   - Fill `API_ID`, `API_HASH`, and set a strong `JWT_SECRET`
2. Build and start:
   - `docker compose up --build -d`
   - Podman: `podman compose up --build -d`
3. Open:
   - Frontend: <http://localhost>
   - API docs: <http://localhost/api/docs>
   - Health: <http://localhost/health>
4. Create first admin (inside backend container):
   - `docker compose exec backend tg-copier db create-admin your@email.com yourpassword`

### Docker update to latest local main

After pulling latest changes:

1. Rebuild and restart:
   - `docker compose down`
   - `docker compose up --build -d`
2. Check logs:
   - `docker compose logs -f backend`
   - `docker compose logs -f frontend-proxy`
   - Podman: `podman compose logs -f backend`

### Docker hot-reload mode (optional)

Use this mode for active coding with backend and frontend live reload in containers.

1. Start dev stack:
   - `docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build`
   - Podman: `podman compose -f docker-compose.yml -f docker-compose.dev.yml up --build`
2. Open:
   - Frontend (Vite): <http://localhost:5173>
   - API docs: <http://localhost:8000/api/docs>
3. Stop:
   - `docker compose -f docker-compose.yml -f docker-compose.dev.yml down`
   - Podman: `podman compose -f docker-compose.yml -f docker-compose.dev.yml down`

Notes:

- `frontend-proxy` is disabled in this mode.
- Source changes in `src/` and `frontend/` are reflected automatically.
- If frontend dependencies changed, recreate the dev stack so `npm ci` re-runs.

### Docker troubleshooting

- Port in use: stop local services using ports `80`, `8000`, or `27017`.
- Mongo not ready yet: wait a few seconds and recheck `docker compose logs -f backend`.
- Reset all local container state (destructive):
  - `docker compose down -v`
- CORS/browser errors: open app via `http://localhost` (not a different host).

## Web Panel

- **Admin panel** (`/admin/*`): Manage users, view all mappings, logs, workers.
- **User panel** (`/dashboard`, `/accounts`, `/mappings`, etc.): Manage your Telegram accounts, channel mappings, filters, and workers.

## Filters

Filters control which messages are copied from a source channel to a destination channel. Each mapping can have one or more filters. **All filters must pass** (AND logic): a message is copied only if it satisfies every filter rule.

### Filter rule types

| Rule | Description | Example |
| --- | --- | --- |
| **Include text** | Message must contain this text | `announcement` → only messages with "announcement" |
| **Exclude text** | Message must NOT contain this text | `spam` → skip messages containing "spam" |
| **Media types** | Only copy messages of these types | `text`, `voice`, `video`, `photo`, `other` |
| **Regex pattern** | Message text must match this regex | `#\d+` → messages with hashtags followed by digits |

### Examples

1. **Copy only text announcements**: Include text `announcement`, Media types `text`.
2. **Copy voice and video, exclude spam**: Media types `voice`, `video`; Exclude text `spam`.
3. **Copy messages with order IDs**: Regex pattern `#\d+` (e.g. matches "order #123").

## Transformations (text replacement before forwarding)

Mappings can also apply transform rules before sending to destination channels:

- **Text replacement**: replace plain text (e.g. `Sam channel` -> `Tom channel`)
- **Regex replacement**: replace text using regex patterns
- **Emoji replacement**: replace icons/emoji (e.g. `🔥` -> `⭐`)
- **Media replacement**: upload reusable media assets and replace incoming media (photo/video/voice)
- **Template rendering**: build final message/caption using placeholders, e.g.
  `"[{{source_chat_title}}] {{text}} (#{{message_id}})"`

Transform rules are applied in priority order for each matched mapping, then the transformed
message/caption is delivered. Media/template rules can be scoped by message/media type.

**PII presets (web UI):** The mapping detail page can insert common regex redaction rules (emails, phone-like strings, etc.) as ordinary `regex` transforms. These are **client-side shortcuts** only; the API does not treat them differently from manually created transforms. Review patterns for false positives before relying on them in production.

## VPS Deployment (Ubuntu)

Deploy on a fresh Ubuntu 20.04/22.04/24.04 VPS. The script installs nginx, Python 3.11+, Node.js 20, clones the repo, builds the frontend, configures systemd, and sets up nginx as a reverse proxy.

### One-line deploy (recommended)

```bash
curl -fsSL "https://raw.githubusercontent.com/sammirzagharcheh/PyTelegramClientCopier/main/scripts/deploy-ubuntu.sh" | sudo bash
```

**Alternative (clone and run)** – always uses the latest script:

```bash
git clone https://github.com/sammirzagharcheh/PyTelegramClientCopier.git /tmp/tgc
sudo bash /tmp/tgc/scripts/deploy-ubuntu.sh
```

> **Troubleshooting:** If you see `-u: command not found` or `-E: command not found` when using `curl | sudo bash`, the raw script may be cached. Use the clone-and-run alternative above, or pipe through: `sed 's/\$SUDO -u "\$APP_USER"/runuser -u "\$APP_USER" --/g'`

### After deploy: configure .env and create admin

If the script ran non-interactively (no TTY), configure `.env` and create the admin user:

```bash
sudo nano /opt/telegram-copier/.env
```

Set: `API_ID`, `API_HASH` (from [my.telegram.org](https://my.telegram.org)), and `JWT_SECRET` (e.g. `openssl rand -hex 32`). Then initialize the DB and create the admin (run as app user `tgcopier` for correct file ownership):

```bash
sudo -u tgcopier bash -c "cd /opt/telegram-copier && .venv/bin/tg-copier db init-db"
sudo -u tgcopier bash -c "cd /opt/telegram-copier && .venv/bin/tg-copier db create-admin your@email.com yourpassword"
sudo systemctl restart telegram-copier
```

### Environment variables (optional)

- `INSTALL_DIR` – Installation directory (default: `/opt/telegram-copier`)
- `DOMAIN` – Domain name for nginx (e.g. `copier.example.com`)
- `USE_SSL=true` – Enable Let's Encrypt HTTPS
- `CERTBOT_EMAIL` – Email for Let's Encrypt
- `SKIP_DEPS=true` – Skip system package install (if already done)
- `UPDATE_ONLY=true` – Pull, rebuild, restart only (for quick redeploy)
- `NON_INTERACTIVE=true` – Use env vars only, no prompts
- `API_ID`, `API_HASH`, `JWT_SECRET` – For non-interactive setup
- `ADMIN_EMAIL`, `ADMIN_PASSWORD` – Admin credentials for non-interactive setup

### Deployment Examples

With HTTPS:

```bash
DOMAIN=copier.example.com USE_SSL=true CERTBOT_EMAIL=you@example.com \
  curl -fsSL "https://raw.githubusercontent.com/sammirzagharcheh/PyTelegramClientCopier/main/scripts/deploy-ubuntu.sh" | sudo bash
```

Non-interactive (CI/automation):

```bash
API_ID=123 API_HASH=abc JWT_SECRET=xxx ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD=secret \
  NON_INTERACTIVE=true curl -fsSL "https://raw.githubusercontent.com/sammirzagharcheh/PyTelegramClientCopier/main/scripts/deploy-ubuntu.sh" | sudo bash
```

Update only (after initial deploy):

```bash
UPDATE_ONLY=true curl -fsSL "https://raw.githubusercontent.com/sammirzagharcheh/PyTelegramClientCopier/main/scripts/deploy-ubuntu.sh" | sudo bash
```

Quick update (run on VPS after SSH):

```bash
ssh user@your-vps-ip
sudo bash /opt/telegram-copier/scripts/update-vps.sh
```

The script pulls latest, rebuilds, and restarts. Alternatively, use `UPDATE_ONLY=true` with the deploy script (see above) to fetch the latest script from GitHub.

### Production checklist

Before going live:

- [ ] Set `JWT_SECRET` to a strong random value (script auto-generates if not provided)
- [ ] Use `USE_SSL=true` with a domain for HTTPS
- [ ] Ensure DNS A record points domain to your VPS before running with SSL
- [ ] Configure firewall (e.g. `ufw allow 'Nginx Full' && ufw enable`)
- [ ] Keep `API_ID` and `API_HASH` confidential (from my.telegram.org)
- [ ] For non-interactive deploy, avoid passing secrets in shell history; use a secrets file or CI variables

## Tests

**Backend (Python):**

- `pytest`
- `pytest tests/unit`
- `pytest tests/api`
- `pytest tests/integration`
- `pytest tests/functional`

**Frontend (Vitest):**

- `cd frontend && npm run test`

### Live Telegram integration test

1. Add to `.env`:
   - `API_ID` and `API_HASH` (from my.telegram.org)
   - `BOT_TOKEN` (from @BotFather; create a bot and use its token)
   - `TELEGRAM_TEST_CHAT_ID` (optional; chat ID to send a test message)
2. Run: `pytest tests/integration/test_telethon_live.py`

## Database Migrations Helper Scripts

Use helper scripts to run Alembic migrations per environment database (`dev`, `test`, `prod`).

PowerShell (Windows):

```powershell
$env:PGPASSWORD = "your-postgres-password"
./scripts/migrate.ps1 -Environment dev -Action upgrade -Revision head
./scripts/migrate.ps1 -Environment test -Action current
./scripts/migrate.ps1 -Environment prod -Action downgrade -Revision -1
```

Shell (Linux/macOS):

```bash
export PGPASSWORD='your-postgres-password'
./scripts/migrate.sh dev upgrade head
./scripts/migrate.sh test current
./scripts/migrate.sh prod downgrade -1
```

Optional connection overrides:

- `PGUSER` (default `8n8user`)
- `PGHOST` (default `localhost`)
- `PGPORT` (default `5432`)
