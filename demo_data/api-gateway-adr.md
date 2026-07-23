# ADR: API Gateway Upstream Timeouts

## Context

Northstar Cloud routes external traffic through a shared API gateway with per-service upstream timeouts.

## Decision

Default upstream timeout is 10 seconds. Services with p95 latency above 5 seconds require explicit timeout review before gateway changes.

## Consequences

Lowering timeouts without service review can cause 502 errors during deploys that add latency (see incident-2025-08-billing-502.md).
