# INFRA-003 Implementation Note

## Summary

Added SQLAlchemy ORM models for all 12 core tables from the data model, Alembic migration infrastructure, and an initial revision that enables the pgvector extension and creates indexes (including HNSW on embeddings). Migrations run via `alembic upgrade head` using `DATABASE_URL` from settings.

## Files Changed

| File | Purpose |
|------|---------|
| `app/infrastructure/db/base.py` | Declarative base and model import registry for Alembic |
| `app/infrastructure/db/enums.py` | PostgreSQL enum types mapped to Python enums |
| `app/infrastructure/db/session.py` | Engine, session factory, and `get_db()` dependency |
| `app/modules/users/models.py` | `users` table |
| `app/modules/workspaces/models.py` | `workspaces`, `workspace_members` tables |
| `app/modules/documents/models.py` | `documents` table |
| `app/modules/ingestion/models.py` | `document_chunks`, `ingestion_jobs` tables |
| `app/modules/rag/models.py` | `conversations`, `messages` tables |
| `app/modules/agents/models.py` | `agent_runs`, `agent_tool_calls` tables |
| `app/modules/usage/models.py` | `usage_events` table |
| `app/modules/audit/models.py` | `audit_logs` table |
| `app/migrations/env.py` | Alembic environment wired to `DATABASE_URL` |
| `app/migrations/versions/001_initial_core_schema.py` | Initial migration (pgvector + all tables/indexes) |
| `alembic.ini` | Alembic configuration |
| `pyproject.toml` | Added sqlalchemy, alembic, psycopg2-binary, pgvector; dev testcontainers |
| `tests/conftest.py` | Added `minimal_env` fixture and DB engine reset |
| `tests/unit/test_models.py` | Metadata registration unit tests |
| `tests/integration/test_migrations.py` | Migration integration tests against pgvector Postgres |

## Behavior Added

- `alembic upgrade head` applies the initial schema to an empty PostgreSQL database with pgvector.
- `CREATE EXTENSION IF NOT EXISTS vector` runs in the first migration.
- All tenant-owned tables include `workspace_id` with composite indexes starting with `workspace_id` per data model.
- HNSW index on `document_chunks.embedding` for cosine similarity search.
- SQLAlchemy models live in module folders per module boundaries; Alembic imports them via `import_all_models()`.
- `get_db()` session dependency available for future route/repository wiring.

## Tests Added

**Unit (`tests/unit/test_models.py`):**

- All 12 core tables registered in SQLAlchemy metadata
- Tenant-owned tables include `workspace_id` column

**Integration (`tests/integration/test_migrations.py`):**

- `test_migrations_create_all_core_tables` — empty DB → `alembic upgrade head` → all tables exist, pgvector extension enabled, HNSW index present
- `test_migrations_downgrade_and_upgrade` — downgrade to base and re-upgrade succeeds

Existing config tests (`tests/unit/test_config.py`, 8 tests) continue to pass.

## Decisions Made

- Used synchronous SQLAlchemy with `psycopg2-binary` for Alembic and MVP simplicity; async drivers deferred.
- Placed ORM models in owning module folders (`app/modules/*/models.py`) rather than a central `infrastructure/db/models/` tree.
- Hand-authored initial migration for explicit control over pgvector extension, enum types, and HNSW index.
- Reserved SQL column name `metadata` mapped to Python attribute `metadata_` to avoid shadowing SQLAlchemy `MetaData`.
- Reserved column `input` on `agent_tool_calls` mapped to Python attribute `input_`.
- Document default status not set at DB level — application layer sets status on insert (matches service-layer ownership).

## Known Limitations

- No repositories, seed script, or Docker Compose wiring — deferred to domain stories and INFRA-001/INFRA-004.
- No composite FK `(workspace_id, id)` enforcement at DB level — service layer validates consistency per data model notes.
- Migration tests require Docker (testcontainers) for pgvector Postgres; skipped if Docker unavailable.
- `get_db()` not yet wired into FastAPI routes.
- Downgrade drops enum types; re-upgrade on shared DBs with lingering types may need manual cleanup in edge cases.

## Follow-up Items

- **INFRA-001:** Docker Compose with postgres service and migration init command
- **INFRA-004:** Seed script using migrated schema
- **AUTH-001 / domain stories:** Repositories and services using `get_db()` and ORM models
- **CI (INFRA-005):** Wire `alembic upgrade head` before pytest in GitHub Actions
