# AUTH-003 Implementation Note

## Summary

Added authenticated `POST /auth/logout` returning `204 No Content`. MVP uses stateless JWTs with **no Redis blocklist**; documentation states the client must discard the access token after logout.

## Files Changed

| Path | Change |
|------|--------|
| `app/api/routes/auth.py` | `POST /auth/logout` requires JWT, returns 204 |
| `app/modules/auth/service.py` | `AuthService.logout()` acknowledgment no-op |
| `tests/api/test_auth_logout.py` | API acceptance tests (incl. non-blocklist behavior) |
| `tests/unit/test_auth_service.py` | Unit coverage for logout no-op |
| `docs/06-api-design.md` | Logout notes: client discard, no MVP blocklist |
| `docs/09-security-and-rbac.md` | Logout model clarified for MVP |

Folded into UI-002 delivery; see also [UI-002](./UI-002.md).

## Behavior Added

- Valid Bearer JWT → `204` empty body
- Missing/invalid JWT → structured `401` (existing auth error handlers)
- Same JWT remains valid on `/auth/me` after logout (documents no blocklist)

## Tests Added

- `tests/api/test_auth_logout.py`
- `tests/unit/test_auth_service.py::test_logout_is_noop_acknowledgment`

## Decisions Made

- No Redis `jti` blocklist for MVP (story allows documenting client-side discard)
- Domain method kept as a no-op hook for a future blocklist without changing the route contract

## Known Limitations

- Logged-out tokens remain usable until expiry if retained by a client or attacker
- No audit event for logout in this story

## Follow-up Items

- Optional Redis JWT blocklist (P1 polish per security docs)
- Pair with UI session clear (delivered in UI-002)
