# AUTH-002 Implementation Note

## Summary

Implemented public user login at `POST /auth/login`. Valid credentials are checked against the stored bcrypt hash and return a JWT access token with the same response shape as registration. Invalid credentials return a generic `401 invalid_credentials` response without revealing whether the email exists.

Review fixes: added per-IP login rate limiting (10/min), constant-time credential verification via dummy bcrypt hash on unknown email, and safe handling of malformed stored password hashes.

## Files Changed

| File | Purpose |
|------|---------|
| `app/modules/auth/password.py` | `verify_password`, `DUMMY_PASSWORD_HASH`, malformed-hash handling |
| `app/modules/auth/exceptions.py` | `InvalidCredentialsError` domain exception |
| `app/modules/auth/schemas.py` | `LoginRequest` and `LoginResponse` models |
| `app/modules/auth/service.py` | `AuthService.login` with timing-safe verification |
| `app/infrastructure/rate_limit.py` | In-memory 10/min per-IP login rate limiter |
| `app/api/auth_errors.py` | 401 invalid-credentials and 429 rate-limited handlers |
| `app/api/deps.py` | `enforce_login_rate_limit` dependency |
| `app/api/routes/auth.py` | `POST /auth/login` route with rate-limit dependency |
| `app/main.py` | Registered auth and rate-limit exception handlers |
| `stories/auth-002-user-login.md` | Status set to `in_progress` |
| `tests/unit/test_auth_password.py` | `verify_password` and malformed-hash unit tests |
| `tests/unit/test_auth_schemas.py` | Login request validation tests |
| `tests/unit/test_auth_service.py` | AuthService login unit tests (timing-safe path) |
| `tests/unit/test_rate_limit.py` | In-memory rate limiter unit tests |
| `tests/unit/test_auth_rate_limit.py` | 429 response shape via TestClient (no Docker) |
| `tests/api/test_auth_login.py` | Login API integration tests (rate limit, malformed hash) |

## Behavior Added

- `POST /auth/login` accepts `email`, `password` (8–128 chars).
- Email normalized to lowercase before lookup (consistent with registration).
- Password verified with bcrypt via `verify_password`.
- Success returns `200` with `user`, `access_token`, `token_type: bearer`, `expires_in`.
- Unknown email or wrong password returns `401` with `{ error: { code: invalid_credentials, message, details } }`.
- Invalid payload (short password, bad email) returns `422` via Pydantic validation.
- **Rate limit:** 10 requests/min per client IP; 11th request within the window returns `429` with `Retry-After` header and `{ error: { code: rate_limited, message, details } }`.
- **Timing safety:** When email is not found, `verify_password` still runs against a fixed dummy bcrypt hash before returning `401`.
- **Malformed hashes:** Invalid `password_hash` values in the database are caught by `verify_password` and map to `401`, not `500`.

## Tests Added

**Unit:**

- `verify_password` returns true/false for matching and non-matching passwords
- `verify_password` returns false for malformed bcrypt hashes (no exception)
- `DUMMY_PASSWORD_HASH` is a valid fixed bcrypt hash
- Login schema normalizes email, rejects short password and invalid email
- AuthService login returns user + token; raises `InvalidCredentialsError` for unknown email and wrong password
- Unknown-email path calls `verify_password` with `DUMMY_PASSWORD_HASH`
- Malformed stored hash raises `InvalidCredentialsError` (not server error)
- In-memory rate limiter allows up to N requests and blocks N+1
- Login route returns 429 with `rate_limited` code and `Retry-After` when dependency blocks request

**API (require Docker):**

- Successful login after registration returns valid JWT
- Wrong password returns 401 with `invalid_credentials`
- Unknown email returns same 401 shape (no email-existence leak)
- Short password returns 422
- 11th login attempt within 1 minute returns 429 with `rate_limited` and `Retry-After`
- User with malformed `password_hash` in DB returns 401, not 500

## Decisions Made

- Reused the registration token response shape via a dedicated `LoginResponse` model (same fields as `RegisterResponse`).
- Failed login handled via domain exception + app-level handler (mirrors AUTH-001 duplicate-email pattern).
- Generic error message `"Invalid email or password"` for both missing user and bad password.
- Login route returns `200 OK` per API design (register remains `201 Created`).
- Rate limiting implemented as a FastAPI dependency backed by an in-memory fixed-window limiter (MVP-simple, single-process).
- Dummy bcrypt hash uses a fixed salt at module import so both login paths incur similar CPU cost without per-request hash generation.

## Known Limitations

- In-memory rate limiter is not shared across API replicas or worker processes; production should use Redis or edge rate limiting.
- Validation errors use FastAPI default `detail` array, not full `{ error: { code, message } }` envelope (AUTH-006).
- JWT authentication middleware not yet wired (AUTH-005); token is issued but not consumed by protected routes in this story.

## Follow-up Items

- **Production rate limiting:** Replace in-memory limiter with Redis-backed or reverse-proxy rate limiting for multi-instance deployments.
- **AUTH-005:** JWT authentication middleware to protect workspace routes.
- **AUTH-006:** Unified error response envelope for validation failures.
