# INFRA-005 Implementation Note

## Summary

Added GitHub Actions CI workflow with three jobs: Ruff lint, unit tests, and integration/API/security tests. Tests that require PostgreSQL use testcontainers on the GHA runner (Docker is available on `ubuntu-latest`). Ruff was added to dev dependencies with minimal lint rules (E/F/I/W, line length 100, Python 3.11 target).

## Files Changed

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | CI pipeline: lint, unit tests, integration tests on PR and main push |
| `pyproject.toml` | Added `ruff` to `[project.optional-dependencies].dev`; `[tool.ruff]` config |
| `stories/infra-005-github-actions-ci.md` | Story status → in progress |
| `app/api/routes/documents.py` | Ruff I001: import sort |
| `app/infrastructure/storage/__init__.py` | Ruff I001: import sort |
| `app/infrastructure/storage/local.py` | Ruff F401: remove unused import |
| `app/main.py` | Ruff I001: import sort |
| `app/modules/ingestion/tasks.py` | Ruff I001: import sort |
| `app/modules/usage/service.py` | Ruff F401: remove unused `Decimal` import |
| `tests/api/test_structured_logging.py` | Ruff I001: import sort |
| `tests/unit/test_local_storage.py` | Ruff F841: remove unused variable assignment |
| `tests/unit/test_workspace_service.py` | Ruff I001: import sort |

## Workflow Jobs

| Job | Command | Notes |
|-----|---------|-------|
| `lint` | `ruff check .` | Fails on lint violations |
| `unit-tests` | `pytest tests/unit -q` | No Docker required |
| `integration-tests` | `pytest tests/api tests/integration tests/security -q` | testcontainers spins `pgvector/pgvector:pg16` |

## Environment Variables (CI)

Non-production placeholders only — never use real secrets in the workflow. Set in test jobs for settings validation; integration tests override `DATABASE_URL` via testcontainers fixtures:

- `DATABASE_URL` — placeholder (overridden per test)
- `REDIS_URL` — `redis://localhost:6379/0`
- `JWT_SECRET_KEY` — `ci-test-secret-key`
- `STORAGE_BACKEND` — `local`
- `LLM_PROVIDER` — `openai`
- `OPENAI_API_KEY` — `ci-fake-openai-key` (non-`sk-` prefix to avoid secret-scanner noise)

## Security Hardening (Gate 4 fix cycle)

- Added workflow-level `permissions: contents: read` (least-privilege `GITHUB_TOKEN`)
- Renamed dummy `OPENAI_API_KEY` from `sk-test` to `ci-fake-openai-key`
- Integration job runs `docker info` before pytest to fail fast if Docker is unavailable

## Verification Commands

```bash
pip install -e ".[dev]"
ruff check .
pytest tests/unit -q
pytest tests/api tests/integration tests/security -q   # requires Docker
```

## Local Verification Results (2026-07-13)

- `ruff check .` — All checks passed
- `pytest tests/unit -q` — **230 passed** in 4.35s
- Integration tests not run locally (Docker-dependent; will run on GHA)

## Decisions Made

- Used testcontainers (existing test pattern) rather than GHA service containers — tests already encapsulate Postgres lifecycle and pgvector image selection.
- Three separate jobs for clear failure attribution and parallel execution.
- Minimal Ruff config: import sorting + pyflakes/pycodestyle; E501 ignored (line-length enforced via formatter config only).

## Known Limitations

- Integration job requires Docker on the runner; skipped locally when Docker socket unavailable.
- No mypy/type-check job (optional per story; deferred).
