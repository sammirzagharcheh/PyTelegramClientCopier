# Developer Cheat Sheet

Feature-to-files and test-command map for day-to-day work in this project.

## Feature -> files -> tests

| Feature change | Edit files | Run tests |
|---|---|---|
| Add/edit mapping fields (name/source/dest/account binding) | `src/app/web/schemas/mappings.py`, `src/app/web/routers/mappings.py`, `frontend/src/components/AddMappingDialog.tsx`, `frontend/src/components/EditMappingDialog.tsx`, `frontend/src/pages/user/Mappings.tsx`, `frontend/src/pages/user/MappingDetail.tsx` | `pytest tests/api/test_schedules_api.py`, `pytest tests/integration/test_mapping_service.py`, `cd frontend && npm run test -- src/pages/user/MappingDetail.test.tsx` |
| Change filter matching behavior (include/exclude/media/regex) | `src/app/telegram/handlers.py`, `src/app/services/mapping_service.py` | `pytest tests/unit/test_filters.py tests/functional/test_handler_flow.py` |
| Change filter CRUD API | `src/app/web/routers/filters.py`, `src/app/web/schemas/mappings.py`, `frontend/src/pages/user/MappingDetail.tsx` | `pytest tests/api/test_filters_api.py`, `cd frontend && npm run test -- src/pages/user/MappingDetail.test.tsx` |
| Change schedule logic (pass/fail windows) | `src/app/telegram/handlers.py`, `src/app/services/mapping_service.py` | `pytest tests/unit/test_schedules.py tests/functional/test_handler_flow.py` |
| Change user/mapping schedule APIs | `src/app/web/routers/schedules.py`, `src/app/web/routers/mappings.py`, `src/app/web/schemas/schedules.py` | `pytest tests/api/test_schedules_api.py` |
| Change timezone conversion UI | `frontend/src/components/MappingScheduleForm.tsx`, `frontend/src/lib/formatDateTime.ts`, `frontend/src/pages/user/Schedule.tsx`, `frontend/src/pages/user/MappingDetail.tsx` | `cd frontend && npm run test -- src/components/MappingScheduleForm.test.tsx src/lib/formatDateTime.test.ts src/pages/user/MappingDetail.test.tsx` |
| Change worker start/stop/list/restore behavior | `src/app/web/routers/workers.py`, `src/app/web/app.py`, `src/app/worker.py` | `pytest tests/api/test_workers_api.py tests/integration/test_worker_restore.py` |
| Change forwarding (send_message/send_file/media behavior) | `src/app/telegram/handlers.py`, `src/app/worker.py` | `pytest tests/functional/test_handler_flow.py tests/unit/test_filters.py tests/unit/test_schedules.py` |
| Change reply mapping/index behavior | `src/app/telegram/handlers.py`, `src/app/db/sqlite.py` (if schema), `src/app/db/migrations.py` | `pytest tests/functional/test_handler_flow.py tests/integration/test_reply_mapping.py` |
| Change auth login/refresh/logout/profile | `src/app/web/routers/auth.py`, `src/app/web/deps.py`, `src/app/auth/jwt.py`, `frontend/src/lib/api.ts`, `frontend/src/store/AuthContext.tsx` | `pytest tests/api/test_auth_profile.py tests/api/test_auth_change_password.py` |
| Change account add/login/session flow | `src/app/web/routers/accounts.py`, `src/app/web/routers/accounts_login.py`, `src/app/telegram/client_manager.py`, related frontend account pages | `pytest tests/integration/test_integration_smoke.py tests/api/test_workers_api.py` |
| Change Mongo log listing/query filters | `src/app/web/routers/message_logs.py`, `src/app/web/routers/worker_logs.py`, `src/app/db/mongo.py` | `pytest tests/api/test_message_logs_api.py tests/integration/test_mongo.py tests/integration/test_mongo_indexes.py` |
| DB schema/migration change | `src/app/db/sqlite.py`, `src/app/db/migrations.py`, affected routers/services | `pytest tests/unit/test_migrations.py` plus feature-specific tests |

## Quick command bundles

### Backend targeted regression pack

```bash
pytest tests/unit/test_filters.py tests/unit/test_schedules.py tests/unit/test_migrations.py \
  tests/api/test_filters_api.py tests/api/test_schedules_api.py tests/api/test_workers_api.py \
  tests/api/test_auth_profile.py tests/functional/test_handler_flow.py tests/integration/test_worker_restore.py
```

### Frontend targeted regression pack

```bash
cd frontend && npm run test -- \
  src/components/MappingScheduleForm.test.tsx \
  src/pages/user/MappingDetail.test.tsx \
  src/lib/formatDateTime.test.ts \
  src/lib/queryClient.test.ts
```
