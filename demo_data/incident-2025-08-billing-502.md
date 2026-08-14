# Incident Report: Billing API 502 After Deployment (August 2025)

## Summary

On **2025-08-14**, Northstar Cloud `billing-api` began returning intermittent
**HTTP 502** errors immediately after production deployment **v2.14.0**. Customer
impact concentrated on subscription renewals and invoice generation in the
`payments` namespace.

## Impact

- Gateway 502 rate for upstream `billing-api` peaked at **18%**
- Failed renewals for ~1,200 subscriptions during the 60-minute window
- No evidence of data corruption in `billing-db`; retries succeeded after fix

## Timeline (UTC)

| Time  | Event |
|-------|-------|
| 14:05 | Deployment `billing-api` **v2.14.0** completed |
| 14:12 | API gateway error rate spiked to **18% 502** responses |
| 14:18 | On-call confirmed pods Ready but p95 charge latency ~3.8s |
| 14:25 | Restarted `billing-api`; partial recovery only |
| 14:40 | Root cause: shared gateway upstream timeout lowered to **2s** |
| 15:05 | Hotfix restored gateway timeout to **10s**; error rate normalized |

## Root Cause

A shared API gateway configuration change reduced the upstream timeout for
`billing-api` from **10 seconds to 2 seconds**. Release v2.14.0 added an
extra validation step that raised p95 latency above 2s, so the gateway
terminated healthy upstream work and surfaced **502 Bad Gateway**.

This violated the timeout policy in `api-gateway-adr.md` (default 10s;
explicit review required before lowering).

## Immediate Actions Taken

1. Restarted `billing-api` deployment in `payments` (insufficient alone)
2. Rolled gateway upstream timeout for `billing-api` back to **10 seconds**
3. Added a deployment note requiring gateway timeout review for billing changes
4. Replayed failed renewals via the payment retry worker

## Detection Gaps

- No pre-deploy check compared gateway timeout to recent p95 latency
- Staging smoke tests used a higher gateway timeout than production
- Alerting fired on 502 rate, but timeout config drift was not a dashboard signal

## Follow-ups

1. Add pre-deploy check: gateway timeout ≥ 2× trailing p95 for `billing-api`
2. Expand `billing-api-runbook.md` with explicit gateway timeout verification
3. Align staging edge timeout with production for payment paths
4. Page payments on-call automatically when billing 502 rate > 5% for 5 minutes

## Related Documents

- `billing-api-runbook.md` — first response and restart
- `api-gateway-adr.md` — upstream timeout policy
- `deployment-process.md` — post-deploy verification expectations
