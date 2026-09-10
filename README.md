# Telegram Client Copier

Multi-tenant Telegram copier with admin controls, filtering, and media forwarding.

## Quick start

1. Clone the repo (private GitHub: see [docs/git-clone-and-private-repo.md](docs/git-clone-and-private-repo.md)):
   - Public: `git clone https://github.com/sammirzagharcheh/PyTelegramClientCopier.git && cd PyTelegramClientCopier`
   - Private SSH: `git clone git@github.com:OWNER/REPO.git && cd REPO`
2. Create `.env` with:
   - `API_ID`
   - `API_HASH`
   - `JWT_SECRET` (optional, for auth; set in production)
   - `BOT_TOKEN` (optional, for live Telegram test; from @BotFather)
   - `MONGO_URI` (optional)
   - `MONGO_DB` (optional)
   - `SQLITE_PATH` (optional)
3. Install dependencies:
   - `pip install -e .`
4. Initialize SQLite:
   - `tg-copier db init-db`
5. Create first admin:
   - `tg-copier db create-admin your@email.com yourpassword`
6. Run API server:
   - `tg-copier api`
7. Run the web panel:
   - `cd frontend && npm install && npm run dev`
8. Open <http://localhost:5173> and log in.

## Docker

Full step-by-step guides (with quick start + clone steps in each):

- **[Git clone & private repos](docs/git-clone-and-private-repo.md)** — SSH deploy keys, PAT, `gh`
- **[Docker — production](docs/docker-production.md)** — frontend + backend + MongoDB (port 80)
- **[Docker — production without Mongo](docs/docker-production-no-mongo.md)** — frontend + backend only (optional external Mongo)
- **[Docker — development](docs/docker-development.md)** — hot reload (Vite `:5173` + API reload)

### Production-like (short)

```bash
git clone https://github.com/sammirzagharcheh/PyTelegramClientCopier.git
cd PyTelegramClientCopier
cp docker.env.example docker.env   # PowerShell: Copy-Item docker.env.example docker.env
# Fill API_ID, API_HASH, JWT_SECRET
docker compose up --build -d
docker compose exec backend tg-copier db create-admin your@email.com yourpassword
```

- Panel: <http://localhost> · API docs: <http://localhost/api/docs> · Health: <http://localhost/health>

### Hot-reload (short)

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

- Frontend: <http://localhost:5173> · API: <http://localhost:8000/api/docs>

## Web Panel

- **Admin panel** (`/admin/*`): Manage users, view all mappings, logs, workers.
- **User panel** (`/dashboard`, `/accounts`, `/mappings`, etc.): Manage your Telegram accounts, channel mappings, filters, and workers.

## Filters

Filters control which messages are copied from a source channel to a destination channel. Each mapping can have one or more filters. **All filters must pass** (AND logic): a message is copied only if it satisfies every filter rule.

### Filter rule types

| Rule | Description | Example |
|------|-------------|---------|
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

## VPS Deployment (Ubuntu 22.04+)

Full guide (quick start + clone + step-by-step + manual install): **[docs/deploy-ubuntu.md](docs/deploy-ubuntu.md)**

Private GitHub clone / deploy keys: **[docs/git-clone-and-private-repo.md](docs/git-clone-and-private-repo.md)**

All install docs index: **[docs/README.md](docs/README.md)**

### Clone then deploy (works for private repos)

```bash
git clone git@github.com:OWNER/REPO.git   # or public HTTPS URL
cd REPO
sudo REPO_URL=git@github.com:OWNER/REPO.git bash scripts/deploy-ubuntu.sh
```

### One-line deploy (public repo only)

```bash
curl -fsSL "https://raw.githubusercontent.com/sammirzagharcheh/PyTelegramClientCopier/main/scripts/deploy-ubuntu.sh" | sudo bash
```

Then set `/opt/telegram-copier/.env` (`API_ID`, `API_HASH`, `JWT_SECRET`), create admin, restart — see the Ubuntu guide.

With HTTPS:

```bash
DOMAIN=copier.example.com USE_SSL=true CERTBOT_EMAIL=you@example.com \
  curl -fsSL "https://raw.githubusercontent.com/sammirzagharcheh/PyTelegramClientCopier/main/scripts/deploy-ubuntu.sh" | sudo bash
```

Update on VPS: `sudo bash /opt/telegram-copier/scripts/update-vps.sh`

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
