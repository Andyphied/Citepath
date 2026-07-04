# AUTH-005 Implementation Note

## Summary

Implemented JWT authentication middleware via FastAPI `Depends(get_current_user)`. Bearer tokens are verified with HS256 using `JWT_SECRET_KEY`; missing, expired, malformed, or invalid tokens return structured `401` responses with `unauthorized`, `token_expired`, or `token_invalid` error codes. A protected stub endpoint `GET /auth/session-check` wires the dependency for integration testing.

## Files Changed

| File | Purpose |
|------|---------|
| `app/modules/auth/exceptions.py` | Added `UnauthorizedError`, `TokenExpiredError`, `TokenInvalidError` |
| `app/modules/auth/jwt.py` | Added `decode_access_token` for HS256 verify/decode |
| `app/api/deps.py` | Added `get_current_user`, `CurrentUserDep` with `HTTPBearer` |
| `app/api/auth_errors.py` | Added 401 handlers for auth middleware exceptions |
| `app/api/routes/auth.py` | Added protected stub `GET /auth/session-check` |
| `app/main.py` | Registered new auth exception handlers |
| `stories/auth-005-jwt-authentication-middleware.md` | Status set to `in_progress` |
| `tests/unit/test_auth_jwt_decode.py` | JWT decode unit tests |
| `tests/unit/test_auth_deps.py` | `get_current_user` dependency unit tests |
| `tests/api/test_auth_middleware.py` | Protected endpoint API integration tests |

## Behavior Added

- `HTTPBearer(auto_error=False)` extracts optional Bearer credentials without FastAPI's default 403.
- `decode_access_token` verifies signature/expiry and returns user UUID from `sub`.
- `jwt.decode` uses `options={"require": ["exp", "sub"]}` so correctly signed tokens missing required claims are rejected as `token_invalid`.
- `get_current_user` raises:
  - `UnauthorizedError` when Authorization header is missing
  - `TokenExpiredError` when JWT `exp` is in the past
  - `TokenInvalidError` for malformed tokens, bad signature, missing/invalid `sub`, or deleted user
- Exception handlers return `{ "error": { "code", "message", "details": {} } }` with HTTP `401`.
- `GET /auth/session-check` returns `{ "authenticated": true, "user_id": "<uuid>" }` when JWT is valid.

## Tests Added

**Unit (10 tests):**

- Valid JWT decode returns user id
- Expired JWT raises `TokenExpiredError`
- Malformed JWT raises `TokenInvalidError`
- Wrong secret raises `TokenInvalidError`
- Missing `exp` raises `TokenInvalidError`
- Missing `sub` raises `TokenInvalidError`
- Non-UUID `sub` raises `TokenInvalidError`
- Missing credentials raises `UnauthorizedError` in dependency
- Unknown user id raises `TokenInvalidError` in dependency
- Valid token + existing user returns `User` from dependency

**API (7 tests, require Docker):**

- Valid token on `/auth/session-check` returns 200 with user id
- Missing Authorization header returns 401 `unauthorized`
- Expired token returns 401 `token_expired`
- Token without `exp` returns 401 `token_invalid`
- Malformed token returns 401 `token_invalid`
- Wrong secret returns 401 `token_invalid`
- Unknown user id in token returns 401 `token_invalid`

## Decisions Made

- Auth exceptions live in `app/modules/auth/exceptions.py`; HTTP mapping in `app/api/auth_errors.py` (consistent with AUTH-001/002).
- `get_current_user` placed in `app/api/deps.py` per module boundaries doc.
- Deleted/missing user treated as `token_invalid` (not `unauthorized`) to avoid leaking account state.
- Protected stub at `/auth/session-check` rather than implementing full `GET /auth/me` (AUTH-004 scope).
- `HTTPBearer(auto_error=False)` used so missing token maps to `unauthorized` (401) not FastAPI default 403.

## Known Limitations

- No JWT blocklist/revocation check (logout blocklist is optional P1 per security doc).
- `/auth/session-check` is a middleware verification stub; replace/extend with `GET /auth/me` in AUTH-004.
- Non-Bearer auth schemes (e.g. raw token without scheme) are rejected as `unauthorized`/`token_invalid`.
- AUTH-006 will unify error envelope across all API modules; auth middleware errors already use the target shape.

## Gate 3 Fix (Step 4)

**M1 — Require `exp` claim in JWT decode:** Added `options={"require": ["exp", "sub"]}` to `jwt.decode` in `decode_access_token`. Tokens signed with the correct secret but omitting `exp` (or `sub`) are rejected via PyJWT's required-claim validation and surfaced as `TokenInvalidError` / HTTP 401 `token_invalid`.

**M2 — Tests for missing `exp`:** Added unit test `test_decode_access_token_raises_token_invalid_when_exp_missing` and API test `test_session_check_returns_401_for_token_without_exp`.

## Follow-up Items

- **AUTH-004:** Implement `GET /auth/me` using `CurrentUserDep`
- **AUTH-006:** Consolidate auth error response handling app-wide
- **WS-001+:** Apply `CurrentUserDep` to workspace-scoped routes
