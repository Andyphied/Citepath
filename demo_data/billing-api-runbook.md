# Billing API Runbook

## Overview

The billing-api service handles subscription charges, invoice generation, and payment retries for Northstar Cloud customers.

## Common Symptoms

### HTTP 502 Bad Gateway

502 responses usually indicate the billing-api process is unreachable from the API gateway or an upstream dependency is failing health checks.

## First Response Checklist

1. Confirm recent deployments in the last 24 hours (see deployment-process.md).
2. Check API gateway upstream health for `billing-api`.
3. Verify billing-api pod or process status and restart if unhealthy.
4. Inspect database connection pool saturation on the billing database.
5. Review Redis cache connectivity used for rate limiting metadata.
6. Pull the latest incident notes if a billing outage is active.

## Restart Procedure

```bash
kubectl rollout restart deployment/billing-api -n payments
kubectl rollout status deployment/billing-api -n payments
```

After restart, validate `/health/ready` returns 200 and run a smoke charge in staging.

## Escalation

If 502 persists after restart and upstream health is green, escalate to the payments platform on-call and attach gateway access logs.
