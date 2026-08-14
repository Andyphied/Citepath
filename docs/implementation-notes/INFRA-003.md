# INFRA-003 Implementation Note

## Summary

Alembic migration infrastructure with two revisions: `001_initial_core_schema` (pgvector extension, 12 core tables, workspace-scoped indexes, HNSW on embeddings) and `002_add_workspace_slug` (unique `workspaces.slug`). Migrations run via `alembic upgrade head` using `DATABASE_URL` from settings. Docker Compose includes a one-shot `migrate` service (`alembic upgrade head`) that `api` and `worker` depend on. `get_db()` is defined in `app/infrastructure/db/session.py` and wired into FastAPI routes via `DbSession` in `app/api/deps.py`.

## Files Changed

| File | Purpose |
|------|---------|
| `app/infrastructure/db/base.py` | Declarative base and model import registry for Alembic |
| `app/infrastructure/db/enums.py` | PostgreSQL enum types mapped to Python enums |
| `app/infrastructure/db/session.py` | Engine, session factory, and `get_db()` dependency |
| `app/api/deps.py` | FastAPI `DbSession = Annotated[Session, Depends(get_db)]` wiring |
| `app/modules/users/models.py` | `users` table |
| `app/modules/workspaces/models.py` | `workspaces` (incl. `slug`), `workspace_members` tables |
| `app/modules/documents/models.py` | `documents` table |
| `app/modules/ingestion/models.py` | `document_chunks`, `ingestion_jobs` tables |
| `app/modules/rag/models.py` | `conversations`, `messages` tables |
| `app/modules/agents/models.py` | `agent_runs`, `agent_tool_calls` tables |
| `app/modules/usage/models.py` | `usage_events` table |
| `app/modules/audit/models.py` | `audit_logs` table |
| `app/migrations/env.py` | Alembic environment wired to `DATABASE_URL` |
| `app/migrations/versions/001_initial_core_schema.py` | Initial migration (pgvector + all tables/indexes) |
| `app/migrations/versions/002_add_workspace_slug.py` | Adds unique `slug` column and `ix_workspaces_slug` |
| `alembic.ini` | Alembic configuration |
| `docker-compose.yml` | `migrate` service runs `alembic upgrade head` before API/worker start |
| `pyproject.toml` | sqlalchemy, alembic, psycopg2-binary, pgvector; dev testcontainers |
| `tests/conftest.py` | `minimal_env` fixture and DB engine reset |
| `tests/unit/test_models.py` | Metadata registration unit tests |
| `tests/integration/test_migrations.py` | Migration integration tests against pgvector Postgres |

## Migration Chain

```
<base> → 001_initial_core_schema → 002_add_workspace_slug (head)
```

- **001:** `CREATE EXTENSION IF NOT EXISTS vector`; creates all 12 core tables; composite indexes on tenant tables starting with `workspace_id`; HNSW index `ix_document_chunks_embedding_hnsw`.
- **002:** Adds non-null unique `workspaces.slug` with backfill from `name` (fallback `workspace-{id}`).

## Behavior Added

- `alembic upgrade head` applies the full schema to an empty PostgreSQL database with pgvector.
- `CREATE EXTENSION IF NOT EXISTS vector` runs in the first migration.
- All tenant-owned tables include `workspace_id` with composite indexes starting with `workspace_id` per data model.
- HNSW index on `document_chunks.embedding` for cosine similarity search.
- SQLAlchemy models live in module folders per module boundaries; Alembic imports them via `import_all_models()`.
- `get_db()` session dependency exposed as `DbSession` in `app/api/deps.py` for auth, workspace, and audit services.
- Docker Compose `migrate` service exits 0 on success; `api`/`worker` wait on `service_completed_successfully`.

## Tests Added

**Unit (`tests/unit/test_models.py`):**

- All 12 core tables registered in SQLAlchemy metadata
- Tenant-owned tables include `workspace_id` column

**Integration (`tests/integration/test_migrations.py`):**

- `test_migrations_create_all_core_tables` — empty DB → `alembic upgrade head` → all tables exist, pgvector extension enabled, HNSW index present
- `test_migrations_downgrade_and_upgrade` — downgrade to base and re-upgrade succeeds

Integration tests require Docker (testcontainers + Python `docker` SDK); skipped when Docker socket is unavailable.

## Decisions Made

- Used synchronous SQLAlchemy with `psycopg2-binary` for Alembic and MVP simplicity; async drivers deferred.
- Placed ORM models in owning module folders (`app/modules/*/models.py`) rather than a central `infrastructure/db/models/` tree.
- Hand-authored migrations for explicit control over pgvector extension, enum types, and HNSW index.
- Second migration (`002`) adds `workspaces.slug` separately so initial schema stays stable while workspace routing evolves.
- Reserved SQL column name `metadata` mapped to Python attribute `metadata_` to avoid shadowing SQLAlchemy `MetaData`.
- Reserved column `input` on `agent_tool_calls` mapped to Python attribute `input_`.
- Document default status not set at DB level — application layer sets status on insert (matches service-layer ownership).

## Known Limitations

- No repositories or seed script in this story — seed deferred to INFRA-004.
- No composite FK `(workspace_id, id)` enforcement at DB level — service layer validates consistency per data model notes.
- Migration integration tests require Docker (testcontainers); skipped if Docker daemon/socket unavailable to the Python SDK.
- Downgrade drops enum types; re-upgrade on shared DBs with lingering types may need manual cleanup in edge cases.
- Full `docker compose up` on a host with port 5432 already bound requires stopping the conflicting service or adjusting compose port mapping.

## Follow-up Items

- **INFRA-004:** Seed script using migrated schema
- **INFRA-005:** Wire `alembic upgrade head` before pytest in GitHub Actions
- **Domain stories:** Additional migrations as features land (documents, RAG, agents)

## Close-out verification (2026-07-06)

- `alembic history` / `alembic heads`: linear chain to `002_add_workspace_slug (head)` ✓
- Empty pgvector DB: `upgrade head` creates all 12 tables + `alembic_version`, pgvector extension, HNSW index, `workspaces.slug` ✓
- `downgrade base` → `upgrade head` round-trip succeeds ✓
- `pytest tests/unit/test_models.py`: 2 passed ✓
- `pytest tests/integration/test_migrations.py`: skipped in agent environment (Docker socket not visible to Python SDK); manual container verification performed instead ✓
- `docker compose config`: valid; `migrate` service command `alembic upgrade head` ✓
- `citepath-migrate` image: `alembic current` reports `002_add_workspace_slug (head)` ✓
- Full `docker compose up --build`: build succeeded; stack start blocked by host port 5432 conflict (environment-specific)

## Platform follow-up (2026-07-06)

Hardened migration/integration test coverage per code review notes (no schema or migration changes):

- **`tests/integration/test_migrations.py`:** After `upgrade head`, assert `workspaces.slug` is NOT NULL, `ix_workspaces_slug` exists (unique, on `slug`), and workspace_id-leading composite indexes on representative tenant tables (`documents`, `document_chunks`, `ingestion_jobs`, `audit_logs`).
- **`tests/unit/test_models.py`:** Added `test_workspace_slug_column_matches_migration_expectations` to guard ORM metadata drift for `workspaces.slug` and `ix_workspaces_slug`.
