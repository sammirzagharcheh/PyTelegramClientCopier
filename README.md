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
   - `SQLITE_PATH` (optional)
2. Install dependencies:
   - `pip install -e .`
3. Initialize SQLite:
   - `tg-copier db init-db`
4. Create first admin:
   - `tg-copier db create-admin your@email.com yourpassword`
5. Run API server:
   - `tg-copier api`
6. Run the web panel:
   - `cd frontend && npm install && npm run dev`
7. Open http://localhost:5173 and log in.

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

## VPS Deployment (Ubuntu)

Use the deployment script to deploy on an Ubuntu VPS with nginx:

```bash
curl -fsSL https://raw.githubusercontent.com/sammirzagharcheh/PyTelegramClientCopier/main/scripts/deploy-ubuntu.sh | sudo bash
```

Or clone the repo and run:

```bash
sudo bash scripts/deploy-ubuntu.sh
```

Environment variables (optional):
- `INSTALL_DIR` – Installation directory (default: `/opt/telegram-copier`)
- `DOMAIN` – Domain name for nginx (e.g. `copier.example.com`)
- `USE_SSL=true` – Enable Let's Encrypt HTTPS
- `CERTBOT_EMAIL` – Email for Let's Encrypt
- `SKIP_DEPS=true` – Skip system package install (if already done)
- `UPDATE_ONLY=true` – Pull, rebuild, restart only (for quick redeploy)
- `NON_INTERACTIVE=true` – Use env vars only, no prompts
- `API_ID`, `API_HASH`, `JWT_SECRET` – For non-interactive setup
- `ADMIN_EMAIL`, `ADMIN_PASSWORD` – Admin credentials for non-interactive setup

Example with HTTPS:
```bash
DOMAIN=copier.example.com USE_SSL=true CERTBOT_EMAIL=you@example.com sudo bash scripts/deploy-ubuntu.sh
```

Example non-interactive (CI/automation):
```bash
API_ID=123 API_HASH=abc JWT_SECRET=xxx ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD=secret NON_INTERACTIVE=true sudo bash scripts/deploy-ubuntu.sh
```

Example update only (after initial deploy):
```bash
UPDATE_ONLY=true sudo bash scripts/deploy-ubuntu.sh
```

### Production checklist

Before going live:
- [ ] Set `JWT_SECRET` to a strong random value (script auto-generates if not provided)
- [ ] Use `USE_SSL=true` with a domain for HTTPS
- [ ] Ensure DNS A record points domain to your VPS before running with SSL
- [ ] Configure firewall (e.g. `ufw allow 'Nginx Full' && ufw enable`)
- [ ] Keep `API_ID` and `API_HASH` confidential (from my.telegram.org)
- [ ] For non-interactive deploy, avoid passing secrets in shell history; use a secrets file or CI variables

## Tests

- `pytest`
- `pytest tests/unit`
- `pytest tests/integration`
- `pytest tests/functional`

### Live Telegram integration test

1. Add to `.env`:
   - `API_ID` and `API_HASH` (from my.telegram.org)
   - `BOT_TOKEN` (from @BotFather; create a bot and use its token)
   - `TELEGRAM_TEST_CHAT_ID` (optional; chat ID to send a test message)
2. Run: `pytest tests/integration/test_telethon_live.py`
