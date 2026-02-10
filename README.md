# Telegram Client Copier

Multi-tenant Telegram copier with admin controls, filtering, and media forwarding.

## Quick start

1. Create `.env` with:
   - `API_ID`
   - `API_HASH`
   - `MONGO_URI` (optional)
   - `MONGO_DB` (optional)
   - `SQLITE_PATH` (optional)
2. Install dependencies:
   - `pip install -e .`
3. Initialize SQLite:
   - `tg-copier db init-db`
4. Run API server:
   - `tg-copier api`

## Tests

- `pytest`
- `pytest tests/unit`
- `pytest tests/integration`
- `pytest tests/functional`

### Live Telegram integration test

- Set `API_ID`, `API_HASH`, `BOT_TOKEN`
- Optional: set `TELEGRAM_TEST_CHAT_ID` to send a message
- Run `pytest tests/integration/test_telethon_live.py`
