# Plan: Setup checklist not updating after add account

**Date:** 2026-09-18  
**Status:** Done  
**Architecture SoT:** no architecture change (SPA cache only)

## What / why

After adding a Telegram bot account, returning to the dashboard still shows “Connect a Telegram account” unchecked.

Root cause: `GET /stats/dashboard` correctly derives `setup.account` from SQLite (`accounts_total > 0`). The bot row exists (`telegram_accounts` for the user). The dashboard React Query uses `staleTime: 2 * 60 * 1000`, and account create only invalidates `['accounts']`, not `['stats', 'dashboard']`. Navigating back reuses the pre-create cached `setup`.

## Fix

1. Invalidate `['stats', 'dashboard']` (and admin stats if present) whenever setup-related mutations succeed: account add/delete/edit, mapping create/enable/delete, worker start/stop.
2. Dashboard: `refetchOnMount: 'always'` so revisiting the page always refreshes setup even if a mutation was missed.
3. Extend `Dashboard.test.tsx` / account dialog tests if present; otherwise unit-level note via AddAccountDialog invalidation coverage in a small test or existing dialog test.

## Doc / test

- No architecture.md change.
- Cheatsheet optional one-liner under dashboard setup row.
- Frontend tests for invalidation and/or dashboard refetchOnMount behavior.
