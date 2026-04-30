# Concurrency Control Matrix

Exact race-condition control targets for PostgreSQL runtime paths.

## Scope

This matrix defines:

- high-contention write/read-modify-write paths
- the concurrency hazard per path
- the concrete control used (lock, unique constraint, upsert, retry)
- the expected deterministic outcome
- the test evidence that protects the behavior

## Matrix

| Target file | Hot path | Primary hazard | Control strategy | Deterministic outcome | Test evidence |
| --- | --- | --- | --- | --- | --- |
| `src/app/web/routers/workers.py` | start worker (`_spawn_worker_for_account`) | duplicate starts across concurrent requests/processes | per-account in-process lock + PostgreSQL row lock (`FOR UPDATE`) + unique account reservation row + transient retry (`40P01`, `40001`) | exactly one worker reservation/launch wins per account | `tests/api/test_workers_concurrency_postgres.py::test_spawn_worker_concurrent_start_collision_single_reservation_postgres_mode`, `...::test_retry_wrapper_retries_on_transient_sqlstate` |
| `src/app/web/routers/workers.py` | prune/stop while start in-flight | reservation row (`pid <= 0`) accidentally deleted by concurrent flow | explicit reservation state (`pid <= 0`) preserved in prune and stop flows + start conflict while in-flight | in-flight reservation is never removed by competing path | `tests/api/test_workers_concurrency_postgres.py::test_prune_orphaned_registry_keeps_inflight_reservations`, `...::test_stop_workers_preserves_inflight_reservation_rows` |
| `src/app/telegram/handlers.py` | destination message index save (`_save_dest_mapping`) | duplicate key or lost update under concurrent writes | `INSERT ... ON CONFLICT (...) DO UPDATE` on natural key | one stable row per message mapping key; latest value stored | covered by `tests/integration/test_reply_mapping.py` and parity suite `tests/postgres/test_reply_mapping_postgres.py` |
| `src/app/web/routers/mappings.py` | create/clone/delete mapping with dependent rows | partial writes across parent/child rows under failure/concurrency | atomic transaction boundaries + ordered dependent deletes + `RETURNING id` identity handling | no orphaned child rows and no ambiguous row identity | `tests/integration/test_mapping_service.py`, API mapping suites |
| `src/app/web/routers/filters.py` | filter CRUD on shared mapping | stale writes or duplicate create visibility | single-row update/delete with mapping ownership checks + transaction commit before worker restart | updates are serialized by DB row semantics and reflected consistently | `tests/api/test_filters_api.py` |
| `src/app/web/routers/transforms.py` | transform CRUD on shared mapping | inconsistent transform state under concurrent edits | validated payload merge + single-row update + commit before worker restart | each mutation resolves to a complete valid transform row | transform API tests (`tests/api`), handler flow tests |
| `src/app/services/alert_checker.py` | stale-worker alert emission loop | duplicate webhook storms under repeated scans | in-memory cooldown key per worker (`worker_id:stale_hb`) + heartbeat age threshold | bounded alert rate per worker during stale period | alert checker unit tests |

## Shared Rules (Phase 6.2)

- Retry only transient PostgreSQL concurrency failures: `40P01` (deadlock) and `40001` (serialization failure).
- Do not retry logic/constraint errors (permission, not-found, validation, deterministic integrity failures).
- Lock order is account-centric for worker lifecycle operations.
- Reserved-start rows (`pid <= 0`) represent in-progress work and must be treated as protected state.

## CI Acceptance Gate

- `backend-tests`: `pytest -m "not postgres_concurrency and not postgres_parity"`
- `postgres_concurrency`: `pytest -m "postgres_concurrency"` with retries
- `postgres_parity`: `pytest -m "postgres_parity"` with retries

Phase 6.1 is considered complete only when all three lanes are green.
