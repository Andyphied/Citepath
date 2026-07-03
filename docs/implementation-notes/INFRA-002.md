# INFRA-002 Implementation Note

## Summary

Introduced Pydantic Settings-based configuration and a minimal FastAPI app skeleton. Required environment variables are validated when settings load and when the API starts; missing or invalid values fail fast with descriptive errors.

## Files Changed

| File | Purpose |
|------|---------|
| `app/infrastructure/config.py` | `Settings` class, enums, validators, cached `get_settings()` |
| `app/main.py` | FastAPI app factory with startup validation |
| `.env.example` | Documents all configuration variables |
| `.gitignore` | Ignores `.env`, Python artifacts, local uploads |
| `pyproject.toml` | Project metadata and dependencies |
| `tests/conftest.py` | Settings cache reset and env isolation |
| `tests/unit/test_config.py` | Config validation unit tests |

## Behavior Added

- Application reads configuration from environment variables via Pydantic Settings.
- Required vars (`DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`, `STORAGE_BACKEND`, `LLM_PROVIDER`) must be present before the app starts.
- Conditional validation: S3 backend requires `S3_BUCKET` and `AWS_REGION`; LLM provider requires matching API key.
- Blank `JWT_SECRET_KEY` rejected with a descriptive error (acceptance criterion).
- Unknown env vars are ignored (`extra="ignore"`).
- Run with `uvicorn app.main:create_app --factory` (no module-level app instance).

## Tests Added

`tests/unit/test_config.py` (8 tests):

- Valid minimal env loads settings with defaults
- Missing `JWT_SECRET_KEY` → `ValidationError` mentioning field name
- Blank `JWT_SECRET_KEY` → descriptive "must not be empty" error
- `create_app()` fails when `JWT_SECRET_KEY` is missing
- S3 backend requires `S3_BUCKET` and `AWS_REGION`
- Anthropic provider requires `ANTHROPIC_API_KEY`
- `get_settings()` returns cached singleton
- Unknown env vars are ignored

## Decisions Made

- Used `JWT_SECRET_KEY` (per deployment docs) instead of story shorthand `JWT_SECRET`.
- Placed config in `app/infrastructure/config.py` per module boundaries doc (not `app/core/`).
- No module-level `app = create_app()` — avoids import-time validation before tests set env.
- Python 3.11+ required for `StrEnum`.
- Conditional validation via `@model_validator` rather than separate settings classes per environment.

## Known Limitations

- No health routes, Docker Compose, Alembic, or auth — deferred to later stories.
- Settings cache is process-global; tests must call `reset_settings_cache()` when reloading with different env.
- `.env` file is loaded when present; production should rely on injected env vars / Secrets Manager.
- Copy-paste of `.env.example` with empty `OPENAI_API_KEY=` still fails startup until a key is set.

## Follow-up Items

- **INFRA-003:** Database migrations using `DATABASE_URL` from settings
- **INFRA-001:** Wire `.env.example` into Docker Compose services
- **OBS-001:** Health endpoint with DB/Redis readiness checks
