# AUTH-004 Implementation Note

## Summary

Implemented `GET /auth/me` returning the authenticated user's public profile (`id`, `email`, `name`, `created_at`) via the existing `CurrentUserDep` dependency. Removed the AUTH-005 `/auth/session-check` middleware stub; middleware integration tests now exercise `/auth/me`.

## Files Changed

| File | Purpose |
|------|---------|
| `app/api/routes/auth.py` | Added `GET /auth/me`; removed `/auth/session-check` stub |
| `stories/auth-004-current-user-endpoint.md` | Status set to `in_progress` |
| `tests/api/test_auth_me.py` | Acceptance-criteria API tests for `/auth/me` |
| `tests/api/test_auth_middleware.py` | JWT middleware edge-case tests (no `exp`, wrong secret) |
| `tests/api/test_auth_register.py` | `REPO_ROOT` alembic fixture fix |
| `tests/api/test_auth_login.py` | `REPO_ROOT` alembic fixture fix |

## Behavior Added

- `GET /auth/me` requires a valid Bearer JWT in the `Authorization` header.
- Success returns HTTP `200` with `UserResponse`: `{ "id", "email", "name", "created_at" }`.
- Password hash and other internal fields are never included in the response.
- Missing, expired, malformed, or invalid tokens return HTTP `401` with structured error codes (`unauthorized`, `token_expired`, `token_invalid`) via existing auth exception handlers.

## Tests Added

**API (5 tests in `test_auth_me.py`, require Docker):**

- Valid token returns user profile with expected fields; no password or `updated_at` fields
- Missing Authorization header returns 401 `unauthorized`
- Expired token returns 401 `token_expired`
- Malformed token returns 401 `token_invalid`
- Unknown user ID in JWT returns 401 `token_invalid`

**Updated (2 middleware-only tests in `test_auth_middleware.py`):**

- Token without `exp` claim returns 401 `token_invalid`
- Token signed with wrong secret returns 401 `token_invalid`

**Fixture fix (all auth API test files):**

- `REPO_ROOT` + `monkeypatch.chdir` so Alembic resolves `alembic.ini` under conftest's temp cwd

## Decisions Made

- Reused existing `UserResponse` schema and `CurrentUserDep`; no new service or repository layer needed.
- Removed `/auth/session-check` rather than redirecting — `/auth/me` is the canonical protected auth endpoint per API design doc.
- Handler returns `UserResponse.model_validate(current_user)` to enforce the public response shape at the route boundary.

## Known Limitations

- No JWT blocklist/revocation check (same as AUTH-005; logout blocklist is optional P1).
- Response does not include workspace membership or role context (out of scope; workspace routes provide that separately).

## Follow-up Items

- **AUTH-006:** Consolidate auth error response handling app-wide
- **AUTH-003:** Logout endpoint when implemented should pair with client discarding tokens used against `/auth/me`
