# Telegram Client Copier

Multi-tenant Telegram copier with admin controls, filtering, and media forwarding.

## Quick start

1. Create `.env` with:
   - `API_ID`
   - `API_HASH`
   - `JWT_SECRET` (optional, for auth; set in production)
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

## Tests

- `pytest`
- `pytest tests/unit`
- `pytest tests/integration`
- `pytest tests/functional`

### Live Telegram integration test

- Set `API_ID`, `API_HASH`, `BOT_TOKEN`
- Optional: set `TELEGRAM_TEST_CHAT_ID` to send a message
- Run `pytest tests/integration/test_telethon_live.py`
