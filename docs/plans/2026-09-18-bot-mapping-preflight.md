# Plan: Bot mapping access preflight (bot workers phase 3)

**Date:** 2026-09-18  
**Status:** Done  
**Architecture SoT:** `docs/architecture.md` §2.2 `peer_resolve`; mappings store integer chat IDs; workers stay OS subprocesses

## What / why

Phase 2 resolves `@username` / `t.me` to an integer ID. That only proves Telegram *knows* the peer (public username is enough). A bot can still fail to copy: not a member, not a channel admin, or no post permission.

On **bot** mapping create/update, the API should `get_permissions` on source and dest and return a **clear 400** instead of saving a route that will never copy. User-session mappings skip this (picker already listed their dialogs; a running worker would 409 a second session).

BotFather group privacy cannot be inspected via MTProto. Group source membership is checked; the 400/hint still mentions privacy.

## Architectural impact

- SQLite mapping columns unchanged (integer chat IDs).
- New helper `telegram/peer_access.py`: short-lived bot client (same `start_account_client` / in-memory `StringSession`; token never on argv).
- Call from `POST /mappings` and routing `PATCH /mappings/{id}` after existing validation, **before insert/update**.
- Clone skips preflight (same chats already saved).
- Copy pipeline / workers unchanged.
- No new public endpoint (authoritative on save so API keys cannot skip it).

Checks (bot only):

| Chat | Fail 400 when |
|------|----------------|
| Source channel | Not a member, or not admin/creator |
| Source group | Not a member (privacy: hint only) |
| Destination channel | Cannot post (`post_messages` false and not creator) |
| Destination group | `send_messages` is false |

## Risks + mitigations

| Risk | Mitigation |
|------|------------|
| User worker session locked | Do not preflight user accounts |
| Extra Telegram calls | One client, two `get_permissions`; bots use in-memory session so worker can stay up |
| False 400 on restricted admins | Treat creator or `post_messages`/`send_messages` as writable |
| Existing mapping tests | Account fixture is `user` → no Telethon; bot tests mock helper |

## Doc updates

- Cheatsheet: mapping create + `peer_access`
- Architecture §2.2 `peer_access.py`; §8 bot failure row mentions save-time 400
- Bot hint: save checks membership / post permission
- Bot-workers plan: mark phase 3 done

## Test plan

- Unit: user account is no-op; source channel without admin denied; dest without post denied; happy path admin+post; not-a-participant → denied
- API: bot create mocked ok → 201; bot create denied → 400 and no row; user create still 201 without mock
- Frontend: bot hint mentions the save check; mapping 400 detail is shown

## Implementation order

1. Failing unit + API tests  
2. `peer_access` + mapping router hook  
3. SPA hint  
4. Docs + green gates  
