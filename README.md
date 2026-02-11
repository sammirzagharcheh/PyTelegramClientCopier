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
