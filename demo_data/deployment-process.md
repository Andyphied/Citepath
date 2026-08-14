# Deployment Process

## Standard Release Flow

1. Merge feature branch to `main` after CI passes (unit, integration, security).
2. Tag a release candidate and deploy to **staging**.
3. Run smoke tests, including the billing-api charge flow and auth token issuance.
4. Promote to **production** during the approved change window.
5. Monitor error rates, latency, and gateway upstream health for **30 minutes**
   post-deploy.

## Critical Services Watchlist

After every production deployment that touches payments or edge config, verify:

| Service | Checks |
|---------|--------|
| `billing-api` | `/health/ready` = 200, sample invoice query, 502 rate flat |
| `api-gateway` | Upstream health for `billing-api`, timeout still **10s** unless ADR exception |
| `auth-service` | Token issuance smoke test |
| `billing-db` | Connection pool usage < 80%, no migration lock wait storms |

## Post-Deploy Verification Script

```bash
# Health
curl -sf https://billing.internal/health/ready

# Gateway upstream (example)
kubectl get svc -n edge api-gateway -o wide
kubectl logs -n edge deploy/api-gateway --since=15m | rg "billing-api|502|timeout"
```

If **502 rate exceeds SLO within 15 minutes**, roll back the deployment and
notify `#incidents`. Do not “wait and see” on payment paths.

## Config Change Rules

Each deployment ticket must call out config that affects:

- API gateway upstream timeouts
- Database pool sizes
- Redis timeouts used by billing idempotency keys

The August 2025 billing 502 incident (`incident-2025-08-billing-502.md`) was
caused by a gateway timeout reduction that was not reviewed against p95 latency.

## Rollback

1. Roll back the application deployment to the previous known-good version
2. Revert related edge/config changes in the same change window when applicable
3. Confirm billing-api ready + gateway 502 rate recovered
4. File an incident note before closing the change ticket
