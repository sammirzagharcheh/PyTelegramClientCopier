# Plan: Docker dev overlay ignores bind-mounted src (bot worker 400)

**Date:** 2026-09-18  
**Status:** Done  
**Architecture SoT:** no invariant change; local Docker overlay only

## What / why

Starting a bot worker in local Docker returns **400** even with a valid BotFather token. Chat admin rights are unrelated.

Root cause: `docker-compose.dev.yml` bind-mounts `./src` → `/app/src`, but the image `pip install`s the app into **site-packages**. Uvicorn/`python -c` import that **old** copy. `start_worker` still raises “bot accounts cannot run workers”. The Workers page also has **no error toast**, so Start appears to do nothing.

## Fix

1. Set `PYTHONPATH=/app/src` on the backend service in `docker-compose.dev.yml` so API **and** spawned workers use the mounted tree.
2. Workers UI: `onError` toast with API `detail`.
3. Note in `docs/docker-development.md`. Restart backend after overlay change.

## Test

- Confirm compose overlay contains `PYTHONPATH`.
- Frontend: start mutation error surface (toast) if a Workers test exists; otherwise Mapping-style `errorMessage` wiring.

## Implementation order

1. Compose env + docs  
2. Workers toasts  
3. Recreate backend container  
