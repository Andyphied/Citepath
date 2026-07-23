# Incident Report: Billing API 502 After Deployment (August 2025)

## Summary

On 2025-08-14, billing-api began returning intermittent 502 errors immediately after deployment v2.14.0.

## Timeline

- 14:05 UTC — Deployment v2.14.0 completed
- 14:12 UTC — Gateway error rate spiked to 18% 502 responses
- 14:25 UTC — On-call restarted billing-api; partial recovery
- 14:40 UTC — Root cause identified: gateway timeout lowered to 2s in shared config
- 15:05 UTC — Hotfix rolled gateway timeout back to 10s; error rate normalized

## Root Cause

A shared API gateway configuration change reduced upstream timeout for billing-api below the p95 latency after the deployment introduced an additional validation step.

## Immediate Actions Taken

1. Restarted billing-api deployment
2. Rolled back gateway timeout configuration
3. Added deployment note requiring gateway config review

## Follow-ups

- Add pre-deploy check for gateway timeout regression
- Expand billing-api runbook with gateway timeout verification steps
