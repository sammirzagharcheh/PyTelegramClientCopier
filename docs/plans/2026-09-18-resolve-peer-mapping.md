# Plan: Resolve @username / chat ID for mapping routes (bot workers phase 2)

**Date:** 2026-09-18  
**Status:** Done  
**Architecture SoT:** `docs/architecture.md` §2.2 dialogs; mappings store integer chat IDs

## What / why

Bot mappings require **manual** chat fields (no dialog picker). Operators should paste `@channel`, `t.me/channel`, or a numeric ID. On save, the API resolves that via Telethon `get_entity` using the **same account** that will copy, then stores the integer `chat_id` (and title) as today.

Works for **bot and user** accounts in manual-ID mode. The account must already be able to see the peer (bot in the chat / public username). Invite links (`t.me/+…`) are out of scope.

## Architectural impact

- SQLite `channel_mappings.source_chat_id` / `dest_chat_id` stay integers.
- New API action: `POST /api/accounts/{id}/resolve-peer` `{ query }` → `{ chat_id, title, username, dialog_type }`.
- SPA resolves **on submit** (not per keystroke), then `POST /mappings` with integers.
- Copy pipeline / workers unchanged.
- Short-lived Telethon client (same as dialog listing): user session copy-or-lock; bot in-memory `StringSession`. Token never on argv.

## Risks + mitigations

| Risk | Mitigation |
|------|------------|
| User worker session locked | 409 + same “stop the worker” copy as dialogs |
| Username the bot cannot see | 502 with Telegram-derived message (private / not found) |
| Invite links | 400: use @username or numeric ID after adding the bot |
| Extra Telegram calls | Two `get_entity`s per create/edit of route; no cache required for MVP |

## Doc updates

- Cheatsheet: resolve-peer + mappingValidation
- Architecture §2.2: `peer_resolve.py`
- Mapping bot hint: `@username` or `-100…`
- Bot-workers plan: mark phase 2 done in the later-phases table

## Test plan

- Unit: parse `@name`, `t.me/name`, integers; reject invite links / empty
- Unit: resolve maps mocked `get_entity` to dialog fields; bots call `start_bot_client`
- API: 200 mocked; 400 bad query; 409 locked; 404 other user’s account
- Frontend: `parseChatRef` / validate allows username; Add mapping submit calls resolve then posts ints

## Implementation order

1. Tests for parse + resolve + API  
2. `peer_resolve` + accounts route  
3. SPA submit + placeholders  
4. Docs + green gates  
