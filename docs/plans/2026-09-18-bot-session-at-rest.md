# Plan: Persist bot sessions + encrypt bot credentials at rest (phases 4–5)

**Date:** 2026-09-18  
**Status:** Done  
**Architecture SoT:** `docs/architecture.md` §2.2 client_manager / workers; §10 config; session files today are plaintext Telethon sqlite

## What / why

**Phase 4.** Bot workers currently start from an empty in-memory `StringSession` every time (full bot login). Persist the authorized StringSession at `SESSIONS_DIR/{user_id}/{account_id}.bot.session` so reconnects are faster. Store it as a **StringSession blob**, not a Telethon sqlite file, so API resolve/preflight and the worker can load independent in-memory copies **without session-file locks**.

**Phase 5.** BotFather tokens in SQLite are plaintext. Optional Fernet (`CREDENTIALS_AT_REST_KEY`): seal `bot_token` and the bot session blob. Prefix `enc:v1:` so plaintext rows/files still load. User `.session` sqlite files stay Telethon’s format (unencrypted); wrapping them would break copy-on-start.

Unset key = today’s plaintext behavior.

Token never on CLI.

## Architectural impact

- New helpers: `telegram/at_rest.py`, `telegram/bot_session.py`
- `start_bot_client(token, session_path=?)` loads/saves StringSession file
- Workers + API `start_account_client` pass the bot session path
- Registry remains `bot://{id}` (not a filesystem path)
- Env: `CREDENTIALS_AT_REST_KEY` (Fernet key; empty = off)
- `cryptography` already pulled in via `python-jose[cryptography]`; declare it directly

## Risks + mitigations

| Risk | Mitigation |
|------|------------|
| Encrypted DB without key | Clear error: set `CREDENTIALS_AT_REST_KEY` |
| Key rotation | Out of scope; re-add bots / rewrite files |
| API + worker both connect | Independent StringSession copies; no sqlite lock |
| Tests inserting plaintext tokens | `reveal()` returns plaintext if no `enc:v1:` prefix |

## Doc updates

- Architecture §2.2, §10
- Cheatsheet, env examples, docker-multi-env secrets table
- Bot-workers later-phases 4 and 5 → Done
- WORKER_TROUBLESHOOTING: session file + optional encryption

## Test plan

- Unit: seal/unseal; plaintext passthrough; missing key + `enc:v1:` errors
- Unit: bot session path; start_bot_client with path saves after start
- Unit: worker bot connect passes session path, does not sqlite-copy
- API: create bot with key set stores `enc:v1:`; start worker still validates revealed token

## Implementation order

1. at_rest + bot_session tests  
2. persist StringSession  
3. seal bot_token on write / reveal on use  
4. Docs + green gates  
