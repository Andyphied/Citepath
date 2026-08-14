# Auth Service Architecture

## Responsibilities

The **auth-service** issues JWT access tokens for Northstar Cloud users,
validates sessions, manages OAuth client credentials for internal services,
and publishes security alert emails via `notification-service`.

## Dependencies

| Dependency | Purpose |
|------------|---------|
| `auth-db` (PostgreSQL) | Users, clients, memberships |
| `redis-cache` | Session revocation and short-lived auth rate limits |
| `notification-service` | MFA / suspicious-login emails |

## Token Policy

- Access tokens: HS256 JWT, **24 hour** expiry (local demo default)
- Refresh tokens: rotate on each use
- Service-to-service tokens: short-lived; `billing-api` validates these on charge APIs

## Failure Modes

- Auth outages block **login** across Northstar Cloud products
- Auth outages do **not** directly cause `billing-api` **502** responses unless
  billing-api misconfigures auth middleware and fails readiness
- Redis revocation cache loss can allow briefly stale sessions until TTL expiry

## Operational Notes

When a customer reports “billing is down” and “I cannot log in,” treat auth and
billing as separate tracks. For post-deploy billing 502s with healthy login,
prefer `billing-api-runbook.md` and gateway timeout checks first.
