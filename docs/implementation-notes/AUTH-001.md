# AUTH-001 Implementation Note

## Summary

Implemented public user registration at `POST /auth/register`. Valid requests create a user with bcrypt-hashed password (cost 12), normalize email to lowercase, and return a JWT access token with configurable expiry.

## Files Changed

| File | Purpose |
|------|---------|
| `app/modules/auth/__init__.py` | Auth module package |
| `app/modules/auth/schemas.py` | Register request/response Pydantic models |
| `app/modules/auth/exceptions.py` | `DuplicateEmailError` domain exception |
| `app/modules/auth/password.py` | bcrypt hashing (cost factor 12) |
| `app/modules/auth/jwt.py` | HS256 JWT creation with `sub`, `iat`, `exp` |
| `app/modules/auth/repository.py` | Email lookup and user creation for auth |
| `app/modules/auth/service.py` | `AuthService.register` orchestration |
| `app/modules/users/repository.py` | User profile lookups (`get_by_id`, `get_by_email`) |
| `app/api/deps.py` | FastAPI dependencies: `get_db`, `AuthService` |
| `app/api/auth_errors.py` | 409 duplicate-email exception handler |
| `app/api/routes/auth.py` | `POST /auth/register` route |
| `app/main.py` | Register auth router and exception handler |
| `pyproject.toml` | Added `bcrypt`, `PyJWT`, `email-validator` |
| `stories/auth-001-user-registration.md` | Status set to `in_progress` |
| `tests/unit/test_auth_password.py` | Password hashing unit tests |
| `tests/unit/test_auth_schemas.py` | Request validation unit tests |
| `tests/unit/test_auth_jwt.py` | JWT claims unit tests |
| `tests/unit/test_auth_service.py` | AuthService unit tests with mocked repo |
| `tests/unit/test_auth_repository.py` | AuthRepository IntegrityError handling tests |
| `tests/api/test_auth_register.py` | Registration API integration tests |
| `tests/api/__init__.py` | API test package |

## Behavior Added

- `POST /auth/register` accepts `email`, `password` (8–128 chars), optional `name`.
- Email normalized to lowercase before storage and duplicate check.
- Password hashed with bcrypt cost factor 12; never stored or returned in plaintext.
- Success returns `201` with `user`, `access_token`, `token_type: bearer`, `expires_in` (seconds from `JWT_EXPIRY_HOURS`).
- Duplicate email returns `409` with structured error `{ error: { code: duplicate_email, message, details } }`.
- Invalid payload (short password, bad email) returns `422` via Pydantic validation.

## Tests Added

**Unit (11 tests):**

- Password hashing uses bcrypt cost 12 and verifies correctly
- Register schema normalizes email, rejects short/long password and invalid email
- JWT includes `sub`, `iat`, `exp` with correct expiry
- AuthService creates user + token; raises `DuplicateEmailError` on duplicate
- AuthRepository rolls back and raises `DuplicateEmailError` on email unique constraint violation

**API (4 tests, require Docker):**

- Successful registration persists user and returns valid JWT
- Duplicate email returns 409 with error code
- Short password returns 422
- Long password (>128 chars) returns 422

## Decisions Made

- Auth persistence in `AuthRepository`; profile lookups in `UserRepository` per module boundaries.
- Duplicate email handled via domain exception + app-level handler (not inline in route).
- Auth routes mounted at `/auth/*` (consistent with `/health`, not `/api/v1` prefix yet).
- FastAPI default 422 format for validation errors; structured error envelope deferred to AUTH-006 for non-409 cases.
- JWT expiry sourced from existing `JWT_EXPIRY_HOURS` setting (default 24h → 86400s).

## Known Limitations

- No rate limiting on register (login rate limit is AUTH-002 scope).
- No audit log on registration (not required by story).
- Validation errors use FastAPI default `detail` array, not full `{ error: { code, message } }` envelope (AUTH-006).
- API base path `/api/v1` prefix not applied (consistent with current health endpoint).

## Follow-up Items

- **AUTH-002:** Login endpoint
- **AUTH-004:** `GET /auth/me` using `UserRepository`
- **AUTH-005:** JWT authentication middleware
- **AUTH-006:** Unified error response envelope for all auth failures
