# Database Migration Plan — Billing Schema Q3

## Scope

Add invoice line-item metadata columns and indexes for reporting queries.

## Rollout

1. Expand migration in staging with dual-write validation
2. Run migration during low-traffic window
3. Monitor billing-api query latency and connection pool usage

## Risk

Large migrations can increase billing-api latency and contribute to gateway timeouts if pool sizes are not adjusted before deploy.
