# Plan: Bot accounts fail to load chats in Add mapping

**Date:** 2026-09-18  
**Status:** Done  
**Architecture SoT:** `docs/architecture.md` §2.2 (`dialog_service`, `client_manager`); workers already reject bots

## What / why

Selecting a bot Telegram account in **Add channel mapping** shows “Could not load chats from Telegram” (API `502`).

Root cause (reproduced in local Docker): Telethon `iter_dialogs` → `GetDialogsRequest` raises `BotMethodInvalidError` — bots cannot list dialogs. Secondary bug: `start_bot_client` uses a hardcoded `"bot_session"` file, so sessions can be reused across tokens (Telethon warning observed).

Also observed in local data: account `bot_token` was a display string (`…@newplanetitbot`), not a BotFather token — create should validate token shape.

Product constraint (unchanged): workers require a user session path; bots cannot run workers.

## Fix

1. **`dialog_service`**: for `account_type == "bot"`, do not call Telethon; return empty list. Extend list response with `manual_required: true` so the SPA can opt into manual IDs without treating it as an error.
2. **`client_manager.start_bot_client`**: use in-memory `StringSession` (unique per start) instead of `"bot_session"`.
3. **Account create**: reject clearly invalid bot tokens (expect `digits:secret` BotFather form).
4. **SPA `MappingRouteFields`**: when selected account is bot, auto-enable manual chat IDs, skip/ignore dialog picker error, show short info that bots cannot list chats (and cannot run workers — use a user account to copy).
5. Docs: cheatsheet one-liner; architecture package note if dialog_service behavior is documented.

## Architectural impact

No invariant change. Dialog listing remains API-side Telethon for **user** accounts only; bots use manual IDs already supported by mapping validation.

## Risks + mitigations

| Risk | Mitigation |
|------|------------|
| SPA still shows red error for bots | Return 200 + `manual_required`; UI branches on account type |
| Invalid tokens still stored | Validate on create; user must re-add bot with real token |
| Expectation that bots copy messages | UI copy: workers need user session accounts |

## Doc updates

- `docs/dev-cheatsheet.md` — dialogs / bot manual IDs
- `docs/plans/README.md` — index this plan
- Optional architecture §2.2 note: bots → empty dialogs / manual IDs

## Test plan

- Unit: `list_account_dialogs` for bot returns `[]` without starting client
- Unit/API: bot create rejects bad token; accepts `123:ABC…` shape
- Frontend: MappingRouteFields with bot account enables manual IDs + info banner
- Run: `pytest tests/unit/test_dialog_service.py tests/api/test_account_dialogs_api.py` (+ account create tests if present); `npm run test -- MappingRouteFields`

## Implementation order

1. Failing tests  
2. Backend dialog + client_manager + token validation  
3. SPA MappingRouteFields  
4. Docs + green gates  
