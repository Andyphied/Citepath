# Billing API Runbook

## Overview

The **billing-api** service handles subscription charges, invoice generation,
payment retries, and dunning workflows for Northstar Cloud customers in the
`payments` namespace.

Primary dependencies:

- `billing-db` (PostgreSQL) — invoices, subscriptions, payment attempts
- `redis-cache` — rate-limit metadata and short-lived idempotency keys
- `api-gateway` — public ingress; upstream name `billing-api`
- `auth-service` — service-to-service JWT validation for charge endpoints

## Common Symptoms

### HTTP 502 Bad Gateway

502 responses from the gateway usually mean **billing-api is unreachable**,
timing out, or failing readiness while the gateway still accepts traffic.

Typical causes after a deploy:

1. Upstream timeout too low relative to p95 latency (see `api-gateway-adr.md`)
2. Pod crash loop / failed readiness on `/health/ready`
3. Billing database connection pool exhaustion
4. Redis connectivity loss affecting idempotent charge paths

### Elevated charge latency without 5xx

If p95 charge latency climbs but success rate stays healthy, check the new
validation steps introduced in recent releases and confirm gateway timeout
headroom remains ≥ 2× p95.

## First Response Checklist

Use this order during an active billing incident:

1. Confirm deployments in the last 24 hours (`deployment-process.md`) and note
   the release version (example: `billing-api` v2.14.0).
2. Check API gateway upstream health for `billing-api` and current upstream
   timeout (expected default: **10 seconds**).
3. Verify billing-api pod/process status; restart if unhealthy.
4. Inspect `billing-db` connection pool saturation and slow queries.
5. Review Redis connectivity used for rate limiting and idempotency keys.
6. Pull active incident notes (example: `incident-2025-08-billing-502.md`).

## Gateway Timeout Verification

```bash
# Confirm upstream timeout for billing-api (expect 10s unless an ADR exception exists)
kubectl get envoyfilter -n edge billing-api-timeout -o yaml | rg -n "timeout|billing-api"
```

If timeout was recently lowered below 10s without a reviewed latency budget,
treat that as a high-probability 502 cause during deploys that add request work.

## Restart Procedure

```bash
kubectl rollout restart deployment/billing-api -n payments
kubectl rollout status deployment/billing-api -n payments
kubectl logs -n payments deploy/billing-api --tail=200
```

After restart:

1. Confirm `/health/ready` returns **200**
2. Run a staging smoke charge (`POST /v1/charges/smoke`)
3. Watch gateway 502 rate for `billing-api` for 15 minutes

## Escalation

If 502s persist after restart **and** upstream health is green:

1. Escalate to **payments platform on-call**
2. Attach gateway access logs for the incident window
3. Include deploy version, gateway timeout value, and DB pool metrics
