# OBS-BATCH-001 Implementation Note

Batch: **OBS-005** + **OBS-007** — Phase 2 OBS reliability closeout  
Implementation split: application layer first, then platform/ops.

## Batch Summary

The application layer delivers ingestion terminal-failure observability (structured logs, atomic failed status, Prometheus failure/duration metrics) and app-layer worker visibility (heartbeat logs, readiness queue depth, admin `pending_count`). Platform/ops owns compose/worker ops tuning, optional Flower, and operator smoke that queue depth drains under load.

## OBS-005 — Ingestion Failure Handling

### Summary

On terminal ingestion failure, the worker marks job + document `failed` in one commit, emits `ingestion_job_failed` with ids + stack, and increments `ingestion_failures_total` / observes `ingestion_duration_seconds` against the OBS-006 metrics surface. Builds on ING-007 retry/fail paths without rewriting the ingestion stack.

### Behavior Added

- Atomic fail: single `session.commit()` for job + document status
- Structured log fields: `job_id`, `document_id`, `workspace_id`, `error_type`, `error_message`, `duration_seconds`, plus `exc_info` or `stack_info`
- Persisted `error_message` sanitized (no storage paths) via existing sanitizer
- Metrics: `ingestion_failures_total{error_type}`, `ingestion_duration_seconds{status}`
- Storage read: permanent vs retryable I/O classification (timeouts/connection → Celery retry)

### Files Changed (2a)

| File | Purpose |
|------|---------|
| `app/modules/observability/metrics.py` | Failure counter + duration histogram helpers |
| `app/modules/ingestion/tasks.py` | Atomic fail, logging, metrics, storage I/O classify |
| `docs/10-ingestion-pipeline.md` | Failure status / metrics docs |
| `docs/11-observability.md` | Ship failure + duration metrics |
| `tests/unit/test_ingestion_tasks.py` | Failure log/metrics + storage retry + atomic asserts |
| `tests/unit/test_metrics.py` | New metric helpers |
| `tests/api/test_metrics_endpoint.py` | Scrape includes new series |

### Tests Added

- Extraction failure → failed job + structured log + `observe_ingestion_failure` / duration
- Transient storage read timeout → Celery retry (not terminal fail)
- Existing failure tests updated for atomic attribute + single-commit path

### Decisions Made

- Metric name `ingestion_duration_seconds` per OBS-005 story (docs previously deferred `ingestion_job_duration_seconds`)
- Bounded `error_type` labels to avoid cardinality explosion
- Sanitize at write time so admin/API surfaces stay client-safe

### Known Limitations

- Worker-local Prometheus counters still not visible on API scrape without multiprocess/Pushgateway
- Unexpected uncaught exceptions outside classified paths still propagate (pre-existing)

## OBS-007 — Background Worker Visibility (app layer)

### Summary

Celery workers emit structured heartbeats on an env-configurable interval. `/health/ready` exposes Redis Celery queue depth. ADMIN-002 list response includes workspace `pending_count`.

### Behavior Added

- `WORKER_HEARTBEAT_INTERVAL_SECONDS` (default 300) → `worker_heartbeat` log via Celery `worker_ready` daemon thread
- `GET /health/ready` adds `queue_depth` and nested `worker: { status, queue_depth }`
- `GET .../admin/ingestion-jobs` adds `pending_count` (DB pending jobs)
- `CELERY_DEFAULT_QUEUE` (default `celery`) for Redis `LLEN`

### Files Changed (2a)

| File | Purpose |
|------|---------|
| `app/modules/observability/worker_heartbeat.py` | Heartbeat emitter + Celery signal registration |
| `app/infrastructure/health_checks.py` | Queue depth probe + readiness payload |
| `app/api/routes/health.py` | Typed readiness response |
| `app/infrastructure/config.py` | Heartbeat + queue name settings |
| `app/modules/ingestion/job_repository.py` | `count_by_status` |
| `app/modules/admin/schemas.py` / `service.py` | `pending_count` on job list |
| `.env.example` | Document new env vars |
| Docs: `11-observability`, `10-ingestion-pipeline`, `06-api-design` | Behavior sync |
| Tests: health, heartbeat, admin unit/API | Coverage |

### Out of scope for the application layer (handoff to platform)

- Docker Compose worker concurrency / resource tuning
- Flower (optional dev tool)
- Operator smoke proving queue depth decreases over time under a real worker drain
- Multiprocess metrics aggregation for worker Prometheus scrapes

## Platform handoff (complete)

Platform follow-up:

1. Verify compose `worker` service starts and emits `worker_heartbeat` at configured interval — **done**
2. Optionally document/enable Flower for local debugging (not required prod) — **done** (`--profile flower`)
3. Smoke: enqueue several ingestion jobs, confirm `/health/ready.queue_depth` trends down while worker healthy — **done** (see evidence below)
4. Confirm env vars documented in README/compose if needed for operators — **done**
5. Do not rework app-layer heartbeat/health/admin contracts unless ops requires it — **honored** (only `task_default_queue` aligned to `CELERY_DEFAULT_QUEUE`)

## OBS-007 — Platform layer

### Summary

Compose wires `WORKER_HEARTBEAT_INTERVAL_SECONDS` and `CELERY_DEFAULT_QUEUE` into `api`/`worker`. Celery `task_default_queue` follows the same setting so Redis `LLEN` matches the broker queue. Optional Flower is a compose profile (local only). Operator docs updated in README / deployment / observability docs.

### Behavior Added

- Compose env interpolation for heartbeat interval + queue name (defaults 300 / `celery`)
- `create_celery_app()` sets `task_default_queue=settings.CELERY_DEFAULT_QUEUE` (ops alignment; API shape unchanged)
- Optional `flower` service via `docker compose --profile flower up` → http://localhost:5555
- README operator table + debug commands for heartbeat logs and queue depth

### Files Changed (2b)

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Env wiring for OBS-007; optional Flower profile |
| `app/infrastructure/celery_app.py` | Align `task_default_queue` with depth probe key |
| `tests/unit/test_celery_app.py` | Assert default queue name |
| `README.md` | Operator env vars + Flower/heartbeat commands |
| `.env.example` | Note compose interpolation / queue alignment |
| `docs/12-deployment-architecture.md` | Env table, Flower, queue key notes |
| `docs/11-observability.md` / `docs/10-ingestion-pipeline.md` | Local ops pointers |
| `stories/obs-007-*.md` | Note pointer updated (status still `in_progress`) |

### Decisions Made

- Redis queue key remains `celery` (Celery/kombu default list); confirmed via live `LLEN` == `/health/ready.queue_depth`
- Flower uses official `mher/flower:2.0` image behind compose profile — no Flower dep in app image / prod
- Host port clash during smoke (`luso-db-1` on 5432) handled with ephemeral override `5433:5432`; repo compose still publishes `5432:5432`

### Smoke Evidence (2026-08-03)

Stack: `WORKER_HEARTBEAT_INTERVAL_SECONDS=30 docker compose -f docker-compose.yml -f /tmp/citepath-smoke-ports.yml up -d postgres redis migrate api worker`

| Check | Result |
|-------|--------|
| Worker env | `WORKER_HEARTBEAT_INTERVAL_SECONDS=30`, `CELERY_DEFAULT_QUEUE=celery` |
| Heartbeat log | `worker_heartbeat_started` + `worker_heartbeat` at interval 30s on `worker_ready` |
| Ready baseline | `queue_depth=0`, `worker.status=ok` |
| Enqueue with worker stopped | 5× `process_ingestion_job.delay(...)` → `/health/ready.queue_depth=5`, Redis `LLEN celery=5` |
| Worker restart drain | depth `5` → `0` within ~6s; final ready `queue_depth=0`, `worker.status=ok` |

Flower profile validated via `docker compose --profile flower config --services` (includes `flower`); image not required for AC.

### Known Limitations

- Compose host `5432` may conflict with other local Postgres containers; internal service DNS is unaffected — remap host port via override if needed
- Worker Prometheus counters still process-local (unchanged from 2a)

## Verification (application layer)

```bash
source .venv/bin/activate
pytest \
  tests/unit/test_ingestion_tasks.py \
  tests/unit/test_metrics.py \
  tests/unit/test_health.py \
  tests/unit/test_worker_heartbeat.py \
  tests/unit/test_admin_service.py \
  tests/api/test_metrics_endpoint.py \
  -v
```

API admin pending_count covered in `tests/api/test_admin_dashboard.py` (requires test DB).

## Verification (platform layer)

```bash
docker compose config
WORKER_HEARTBEAT_INTERVAL_SECONDS=30 docker compose up --build -d postgres redis migrate api worker
curl -s http://localhost:8000/health/ready
docker compose logs worker | grep worker_heartbeat
# Optional: docker compose --profile flower up
pytest tests/unit/test_celery_app.py tests/unit/test_worker_heartbeat.py tests/unit/test_health.py -q
```

## Phase 2 OBS exit evidence

| Story | App | Platform | Status |
|-------|----------|---------------|--------|
| OBS-005 | Atomic fail + structured logs + failure/duration metrics | n/a | `in_progress` (pending acceptance) |
| OBS-007 | Heartbeat + ready queue_depth + admin pending_count | Compose env, queue key align, Flower profile, drain smoke | `in_progress` (pending acceptance) |

Acceptance (OBS-007): jobs in queue + healthy worker → queue depth decreases — **demonstrated** in smoke above.

## Story Status

Both stories remain `in_progress` until after full-batch review and commit.

## Review fix cycle

Addressed review must-fix / small follow-ups without expanding batch scope:

| Item | Resolution | Evidence |
|------|------------|----------|
| `worker.status` /health semantics | Documented that `worker.status` = Redis queue probe success only; process liveness via `worker_heartbeat` + queue drain. Fixed stale `/health` → `/health/ready`. | `docs/10-ingestion-pipeline.md`, `docs/11-observability.md`, `docs/06-api-design.md`, `health_checks.readiness_payload` docstring |
| `queue_depth: 0` vs probe failure | Documented sentinel: probe failure coerces `queue_depth` to `0` with `worker.status=error`; true empty is `0` + `ok`. Kept coerce (no API null change). | Same docs + `app/infrastructure/health_checks.py` |
| Admin `error_message` defense-in-depth | `_job_item` re-sanitizes via `sanitize_ingestion_error_message`. | `app/modules/admin/service.py`, `tests/unit/test_admin_service.py` |
| Path-bearing FileNotFoundError test | Unit test asserts persisted `job.error_message` has no absolute path. | `tests/unit/test_ingestion_tasks.py` |
| Flower bind/auth | Tiny compose/README comment: host bind without auth, local/dev only. | `docker-compose.yml`, `README.md` |
