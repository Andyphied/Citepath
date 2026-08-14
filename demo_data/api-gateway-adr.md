# ADR: API Gateway Upstream Timeouts

## Status

Accepted — 2025-06-02

## Context

Northstar Cloud routes external traffic through a shared API gateway with
per-service upstream timeouts. Payment paths (`billing-api`) are especially
sensitive: a timeout that is too aggressive converts slow-but-successful
upstream work into **HTTP 502** responses for customers.

Historical p95 for `billing-api` charge endpoints sits near **1.5–4.0 seconds**
depending on validation features enabled in a release.

## Decision

1. **Default upstream timeout is 10 seconds** for all services unless an
   explicit exception is recorded.
2. Services with p95 latency above **5 seconds** require timeout review before
   any gateway change ships.
3. Lowering a timeout requires:
   - Trailing 7-day p95 and p99 for the upstream
   - Load-test evidence under the new timeout
   - On-call acknowledgment from the owning team (payments for `billing-api`)

## Consequences

- Safer defaults during deploys that add request latency
- Slightly longer worst-case client wait on true upstream hangs
- Lowering timeouts without review can cause production 502s — as seen in
  `incident-2025-08-billing-502.md` when `billing-api` timeout was cut to **2s**
  during release **v2.14.0**

## Operational Guidance

When investigating billing 502s after deploy:

1. Read current upstream timeout for `billing-api` (expect **10s**)
2. Compare against current p95 latency
3. Prefer restoring the ADR default before deep application debugging if the
   timeout was recently changed
