# INFRA-002 — Environment Variable Configuration

**Story:** INFRA-002  
**Status:** Implemented (pending Gate 6 completion)  
**Date:** 2026-07-03

## Summary

Introduced Pydantic Settings-based configuration and a minimal FastAPI app skeleton. Required environment variables are validated on startup; missing or invalid values fail fast with descriptive errors.

## Implementation

### `app/infrastructure/config.py`

- `Settings` class using `pydantic-settings` with all variables from [deployment architecture](../12-deployment-architecture.md).
- Required: `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`, `STORAGE_BACKEND`, `LLM_PROVIDER`.
- Conditional: `S3_BUCKET`/`AWS_REGION` when `STORAGE_BACKEND=s3`; provider API keys when `LLM_PROVIDER` matches.
- Optional defaults: `JWT_EXPIRY_HOURS`, `EMBEDDING_MODEL`, `CHAT_MODEL`, `RETRIEVAL_MIN_SCORE`, `MAX_UPLOAD_BYTES`, `LOG_LEVEL`, `ENVIRONMENT`, `STORAGE_PATH`.
- `get_settings()` cached singleton; `reset_settings_cache()` for tests.

### `app/main.py`

- `create_app()` factory loads settings before returning FastAPI instance.
- Lifespan hook re-validates settings on API startup.

### `.env.example`

Documents all configuration variables with comments and sensible local defaults.

## Acceptance Criteria

| Given | When | Then |
|-------|------|------|
| Missing `JWT_SECRET_KEY` | API starts (`create_app()`) | `ValidationError` mentioning `JWT_SECRET_KEY` |

## Verification

```bash
pip install -e ".[dev]"
pytest tests/ -k config -v
```

## Out of Scope (later stories)

- Docker Compose (INFRA-001)
- Alembic migrations (INFRA-003)
- Auth routes and JWT middleware (AUTH-*)
- Health endpoint (OBS-001)

## Next Steps

- INFRA-001: Wire `.env.example` into Docker Compose services
- INFRA-003: Database migrations using `DATABASE_URL` from settings
