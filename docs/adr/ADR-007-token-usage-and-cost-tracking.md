# ADR-007: Token Usage and Cost Tracking

## Status

Accepted

## Context

AI calls are the primary variable cost and debugging surface. MVP stories USAGE-001–004 and admin dashboard require visibility into LLM and embedding consumption per workspace. Production-aware systems must show cost awareness.

## Decision

Log **every AI provider call** to `usage_events` synchronously after the call completes (success or failure).

Required fields:
- `workspace_id`, `user_id` (nullable for worker ingestion)
- `provider`, `model`, `operation` (`chat_completion`, `embedding` legacy, `embedding_document`, `embedding_query`, `agent_step`)
- `prompt_tokens`, `completion_tokens`, `embedding_tokens`
- `estimated_cost_usd` from static price table in code (updated manually)
- `latency_ms`, `status`, `metadata` (conversation_id, document_id, agent_run_id, job_id)

Admin API aggregates by day and operation. Usage logging failures must **not** fail user requests — log error and continue.

## Consequences

**Positive:**
- Owners/admins can monitor spend (USAGE-004, ADMIN-004)
- Debug expensive agent runs or ingestion jobs
- Portfolio demonstrates FinOps awareness
- Data supports future billing (explicitly out of MVP)

**Negative:**
- Extra DB write per LLM call (acceptable volume for MVP)
- Cost estimates approximate — not invoice-grade (documented in root README)
- Price table maintenance burden when providers change rates
- Single blended USD/1K rate per model (input/output not split)

## Alternatives Considered

| Alternative | Why not selected |
|-------------|------------------|
| **Provider dashboard only** | No per-workspace attribution |
| **Log files only** | Hard to aggregate for admin API |
| **Sampled logging** | Misses cost spikes; insufficient for demo |
| **Real-time billing enforcement** | Out of MVP scope (A8) |

## Implementation Notes

- `UsageService.log_event()` called from `infrastructure/llm` wrappers, not scattered in routes
- Static `PRICING_USD_PER_1K_TOKENS` dict in `modules/usage/cost_calculator.py`
- Worker ingestion logs with `user_id=null`, metadata includes `document_id`, `job_id`
- Prometheus counter `estimated_ai_cost_usd_total` derived from same calculator for metrics endpoint
- Include failed calls (`status=failed`) for debugging provider issues
