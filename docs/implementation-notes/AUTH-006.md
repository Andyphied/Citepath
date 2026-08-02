# AUTH-006 Implementation Note

## Summary

Confirmed and formally completed AUTH-006 acceptance criteria for consistent auth error responses. Auth failures already used the OBS-004 shared `{ "error": { "code", "message", "details", "request_id" } }` envelope via `app/api/auth_errors.py`. This story adds AC-proof unit/API tests and docs sync; no error-stack rewrite.

## Files Changed

| File | Purpose |
|------|---------|
| `tests/unit/test_auth_errors.py` | Unit AC proof for auth exception handlers and codes |
| `tests/api/test_auth_error_responses.py` | API AC proof for unauthorized / token_* / 422 envelopes |
| `docs/06-api-design.md` | Document `request_id` and auth error codes |
| `docs/implementation-notes/AUTH-006.md` | This note |
| `stories/auth-006-auth-error-responses.md` | Status set to `in_progress` |

## Behavior Added

No new runtime behavior. Inventory of existing AUTH/OBS coverage:

| Code | HTTP | Source | Handler |
|------|------|--------|---------|
| `invalid_credentials` | 401 | `InvalidCredentialsError` (login) | `invalid_credentials_handler` |
| `unauthorized` | 401 | `UnauthorizedError` (missing Bearer) | `unauthorized_handler` |
| `token_expired` | 401 | `TokenExpiredError` (JWT exp) | `token_expired_handler` |
| `token_invalid` | 401 | `TokenInvalidError` (bad JWT / missing user) | `token_invalid_handler` |
| `duplicate_email` | 409 | `DuplicateEmailError` | `duplicate_email_handler` |
| `validation_error` | 422 | `RequestValidationError` (OBS-004) | `request_validation_exception_handler` |
| `rate_limited` | 429 | `RateLimitedError` | `rate_limited_handler` |

All handlers delegate to `app.modules.observability.errors.error_response()` (OBS-004).

## Tests Added

**Unit (`tests/unit/test_auth_errors.py`):**

- `invalid_credentials` → 401 envelope
- `unauthorized` → 401 envelope
- `token_expired` → 401 envelope
- `token_invalid` → 401 envelope
- `duplicate_email` → 409 envelope
- `rate_limited` → 429 + `Retry-After`

**API (`tests/api/test_auth_error_responses.py`):**

- Missing token → `401 unauthorized` with full envelope (no FastAPI `detail`)
- Expired JWT → `401 token_expired`
- Malformed JWT → `401 token_invalid`
- Auth validation (short password on login) → `422 validation_error` (not FastAPI detail array)

**Existing coverage retained:** `tests/api/test_auth_login.py` for `invalid_credentials`; `tests/api/test_auth_me.py` / `test_auth_middleware.py` for token paths.

## Decisions Made

- **No error-stack rewrite** — AUTH-001/002/005 + OBS-004 already ship the required codes and envelope; AUTH-006 is AC proof + docs.
- **Schema owner is OBS-004** — Story note referencing OBS-005 is outdated; shared builder lives in `app/modules/observability/errors.py`.
- **HTTPException handler deferred** — App has no `HTTPException` usage; auth paths raise domain exceptions. Adding a global `HTTPException` normalizer remains optional and is not required for AUTH-006 AC.
- **403** — Auth module returns 401 for credential/token failures; workspace RBAC uses `forbidden` (403) via workspace handlers, outside AUTH-006 code list.

## Known Limitations

- `invalid_credentials` end-to-end API proof still lives in Docker-backed `test_auth_login.py` (needs DB); unit handler test covers envelope shape without Docker.
- Non-auth `HTTPException` / Starlette defaults are not normalized (no current call sites).

## Follow-up Items

- Optional: global `HTTPException` → standard envelope if future code raises FastAPI `HTTPException`.
- Gate 6: mark story `completed` after review/commit.
