# Auth Service Architecture

## Responsibilities

The auth-service issues JWT access tokens, validates sessions, and manages OAuth client credentials for internal services.

## Dependencies

- PostgreSQL for user and client records
- Redis for session revocation cache
- notification-service for security alert emails

## Token Policy

Access tokens expire after 24 hours. Refresh tokens rotate on each use.

## Operational Notes

Auth outages block login for all Northstar Cloud products but do not directly cause billing-api 502 errors unless billing-api misconfigures auth middleware.
