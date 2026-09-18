# Architecture / change plans

Durable planning notes for non-trivial work. The agent writes a plan here **before** implementation (see `.cursor/rules/plan-docs.mdc` and `.cursor/rules/architect-guardian.mdc`).

## Naming

`YYYY-MM-DD-short-slug.md`

## Index

| Date | Plan | Status |
|------|------|--------|
| 2026-09-18 | [Persist bot sessions + encrypt bot credentials](2026-09-18-bot-session-at-rest.md) | Done |
| 2026-09-18 | [Bot mapping access preflight](2026-09-18-bot-mapping-preflight.md) | Done |
| 2026-09-18 | [Resolve @username / chat ID for mapping routes](2026-09-18-resolve-peer-mapping.md) | Done |
| 2026-09-18 | [Docker dev overlay ignores bind-mounted src](2026-09-18-docker-dev-pythonpath.md) | Done |
| 2026-09-18 | [Bot workers alongside user-session workers](2026-09-18-bot-workers.md) | Done |
| 2026-09-18 | [Bot accounts fail to load chats in Add mapping](2026-09-18-bot-dialogs-manual-ids.md) | Done |
| 2026-09-18 | [Setup checklist stale cache after account add](2026-09-18-setup-checklist-stale-cache.md) | Done |
| 2026-09-18 | [Setup checklist, FloodWait retry, skip reasons](2026-09-18-setup-floodwait-skip-reasons.md) | Done |
| 2026-09-11 | [Admin invites](2026-09-11-admin-invites.md) | Done |
| 2026-09-11 | [Safe production update](2026-09-11-safe-prod-update.md) | Guidance (ops) |
| 2026-09-11 | [Auto-backup in update-vps.sh](2026-09-11-update-vps-auto-backup.md) | Done |
| 2026-09-11 | [Prune old VPS backups](2026-09-11-prune-vps-backups.md) | Done |

When a plan is implemented, update its **Status** to `Done` (and note the commit hash if known).
