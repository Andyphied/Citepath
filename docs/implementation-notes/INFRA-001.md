# INFRA-001 Implementation Note

## Summary

Added Docker Compose local stack (API, Celery worker skeleton, PostgreSQL with pgvector, Redis), multi-stage Dockerfile, migration init service, minimal `GET /health` liveness endpoint, and aligned `DATABASE_URL` to the synchronous `psycopg2` driver used by SQLAlchemy and Alembic.

## Files Changed

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Full local stack with healthchecks, migrate init, dev volume mounts |
| `Dockerfile` | Multi-stage Python 3.11 image for API and worker |
| `.dockerignore` | Excludes dev artifacts and secrets from build context |
| `app/main.py` | Registers health router |
| `app/api/routes/health.py` | Minimal liveness `GET /health` |
| `app/infrastructure/celery_app.py` | Celery 5 worker skeleton wired to Redis |
| `.env.example` | `postgresql+psycopg2` URL and Docker host notes |
| `pyproject.toml` | Added `celery[redis]`; dev `pyyaml` for compose tests |
| `tests/unit/test_health.py` | Liveness endpoint unit tests |
| `tests/unit/test_celery_app.py` | Celery app configuration unit tests |
| `tests/unit/test_compose_config.py` | Compose structure unit tests |
| `tests/unit/test_config.py` | Updated DATABASE_URL example to psycopg2 |

## Behavior Added

- `docker compose up --build` starts postgres (pgvector), redis, runs `alembic upgrade head` via `migrate` service, then starts API and worker.
- API exposes `GET /health` returning `{"status": "ok"}` for Compose liveness (DB/Redis readiness deferred to OBS-001).
- Compose embeds dev-default env vars so a fresh clone works without copying `.env`.
- Source bind-mount on `./app` for API/worker hot reload; named volumes for Postgres data and uploads.
- Worker runs `celery -A app.infrastructure.celery_app worker` with MVP broker settings from ADR-004.

## Tests Added

**Unit (`tests/unit/test_health.py`):**

- `test_health_returns_200` — liveness returns 200 and `{"status": "ok"}`

**Unit (`tests/unit/test_celery_app.py`):**

- `test_celery_app_uses_redis_broker` — broker URL, acks_late, time limit, no result backend

**Unit (`tests/unit/test_compose_config.py`):**

- Required services defined (postgres, redis, migrate, api, worker)
- API healthcheck targets `/health` and depends on successful migration
- Shared env uses `postgresql+psycopg2` with Docker service hostnames
- Postgres image is `pgvector/pgvector:pg16`

## Decisions Made

- **DATABASE_URL driver:** Switched `.env.example` from `postgresql+asyncpg` to `postgresql+psycopg2` to match INFRA-003 synchronous SQLAlchemy/Alembic; async driver deferred post-MVP.
- **Liveness only:** `/health` confirms API process is up; readiness with DB/Redis checks belongs in OBS-001.
- **Inline compose env:** Dev defaults in `docker-compose.yml` so fresh clone satisfies acceptance criteria without manual `.env` setup; `.env.example` documents host-native overrides.
- **Migrate as one-shot service:** `migrate` runs `alembic upgrade head` and exits; API/worker wait for `service_completed_successfully`.
- **pgvector extension:** Enabled by Alembic migration (INFRA-003), not a separate init script; postgres image provides pgvector support.

## Known Limitations

- No `/health/ready` or dependency checks — OBS-001.
- Celery tasks not registered yet — ingestion stories (ING-*).
- Worker has no Compose healthcheck — OBS-007.
- Dev bind-mount of `./app` overrides installed package in containers; production image uses baked code only.
- `OPENAI_API_KEY` placeholder in compose satisfies config validation; no LLM calls in this story.
- No README local-setup section yet — INFRA-007.

## Verification

Commands run during implementation and review:

| Command | Result |
|---------|--------|
| `docker compose config` | Valid compose output |
| `docker compose up --build -d` | All services started |
| `curl http://localhost:8000/health` | `{"status":"ok"}` (HTTP 200) in ~20s |
| `docker compose ps` | API **healthy**, postgres/redis **healthy**, worker **up**, migrate **exited 0** |
| `pytest tests/ -v` | 16 passed, 2 skipped (migration integration tests require Docker testcontainers) |

## Follow-up Items

- **OBS-001:** Readiness endpoint with DB and Redis connectivity checks
- **ING-001+:** Register Celery tasks on `celery_app`
- **INFRA-005:** CI service containers mirroring compose stack
- **INFRA-007:** README quickstart with `docker compose up`
