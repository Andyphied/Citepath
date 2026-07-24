# Observability

Production-aware observability for AtlasOps AI MVP without heavy APM infrastructure.

## Structured Logging

- Format: JSON lines to stdout
- Library: `structlog` or `python-json-logger`
- Required fields on every request log:

```json
{
  "timestamp": "ISO8601",
  "level": "info",
  "message": "request_completed",
  "request_id": "uuid",
  "method": "POST",
  "path": "/api/v1/workspaces/.../query",
  "status_code": 200,
  "duration_ms": 1234,
  "user_id": "uuid",
  "workspace_id": "uuid"
}
```

Worker logs include `job_id`, `document_id`, `task_name`.

## Request IDs (OBS-003)

- Middleware reads `X-Request-ID` or generates UUID4
- Attached to `request.state.request_id`
- Returned in response header `X-Request-ID`
- Propagated to Celery tasks via task headers
- Included in all logs and audit metadata for trace correlation

## Error Format (OBS-004)

API errors:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Human readable summary",
    "details": { "field": "reason" },
    "request_id": "uuid"
  }
}
```

Internal errors log full exception with stack; client receives generic `500 internal_error` without stack trace.

Standard codes: `invalid_credentials`, `token_expired`, `token_invalid`, `unauthorized`, `forbidden`, `not_found`, `conflict`, `validation_error`, `rate_limited`, `internal_error`.

## Health Checks (OBS-001)

`GET /health`:

```json
{
  "status": "ok",
  "version": "0.1.0",
  "checks": {
    "database": { "status": "ok", "latency_ms": 5 },
    "redis": { "status": "ok" },
    "storage": { "status": "ok" },
    "worker": { "status": "ok", "pending_jobs": 2 }
  }
}
```

Return `503` if database unreachable. Worker check: ping Redis + optional Celery inspect.

## Ingestion Job Visibility

- Admin API lists jobs with status, error, duration
- Logs: `ingestion_job_completed` with `duration_ms`, `chunk_count`
- Metric: `ingestion_job_duration_seconds` histogram

## Token Usage Logging

Every LLM/embedding call → `usage_events` table (see ADR-007).
Admin rollup: `GET /workspaces/{workspace_id}/admin/usage` (Owner/Admin; default last 7 days).

Additionally log at info level:

```json
{
  "message": "llm_call_completed",
  "provider": "openai",
  "model": "gpt-4o-mini",
  "operation": "chat_completion",
  "prompt_tokens": 1200,
  "completion_tokens": 350,
  "latency_ms": 2100,
  "workspace_id": "..."
}
```

## Agent Tool Call Logging

- Persisted in `agent_tool_calls`
- Log line per tool: `agent_tool_executed` with `tool_name`, `latency_ms`, `status`

## Metrics (OBS-006)

Prometheus-compatible `GET /metrics` (text exposition format via `prometheus_client`).

**Auth / exposure:** Unauthenticated for MVP scraper simplicity. Treat as an internal endpoint — restrict at the network edge (Compose/VPC/firewall). Do not put tenant identifiers in metric labels.

**MVP counters (shipped):**

| Metric | Type | Labels |
|--------|------|--------|
| `http_requests_total` | counter | `method`, `path_template`, `status` |
| `http_errors_total` | counter | `method`, `path_template`, `status` (≥400) |
| `ingestion_jobs_total` | counter | `status` (`pending` / `processing` / `completed` / `failed`) |
| `llm_calls_total` | counter | `operation`, `status` |

- HTTP counters are recorded by `MetricsMiddleware` using route path templates (not raw IDs) to limit cardinality.
- `GET /metrics` itself is excluded from HTTP counters (avoids scrape feedback).
- `ingestion_jobs_total` increments on job create (API process) and status transitions in the worker.
- `llm_calls_total` increments in `UsageService.log_event` (API and worker processes).
- Worker-side increments live in the worker process memory; the API scrape shows API-process counters only unless a shared/multiprocess collector is added later.

**Deferred (histograms / richer series — P2+):**

| Metric | Type | Labels |
|--------|------|--------|
| `http_request_duration_seconds` | histogram | `method`, `path_template` |
| `ingestion_job_duration_seconds` | histogram | `status` |
| `ingestion_failures_total` | counter | `error_type` |
| `rag_query_duration_seconds` | histogram | `insufficient_context` |
| `llm_request_duration_seconds` | histogram | `provider`, `operation` |
| `llm_tokens_total` | counter | avoid `workspace_id` on public scrapes |
| `agent_run_failures_total` | counter | `reason` |
| `estimated_ai_cost_usd_total` | counter | avoid `workspace_id` on public scrapes |

Use path templates (`/workspaces/{workspace_id}/query`) not raw paths to limit cardinality. Prefer admin/usage APIs for per-workspace token and cost rollups.

## Required Metrics (Product)

**OBS-006 MVP (Prometheus scrape):** API request count and error rate; ingestion job status transition counts; LLM/embedding call counts.

All of the following must be derivable (Prometheus and/or logs / admin APIs):

- API request count, latency (`duration_ms` logs today; histogram deferred), error rate
- Ingestion job duration and failure count (counts via `ingestion_jobs_total`; duration histogram deferred)
- RAG query latency (structured logs / future histogram)
- LLM provider latency (usage events + logs / future histogram)
- Token usage by workspace (admin usage API)
- Estimated AI cost by workspace (admin usage API)
- Agent run failures (audit/logs; dedicated counter deferred)

## Minimum Dashboards / Log Views

MVP (CloudWatch or local grep):

1. **API health** — 5xx rate, p95 latency
2. **Ingestion** — failed jobs last 24h, avg duration
3. **AI usage** — tokens and cost by workspace (from admin API or SQL)
4. **Agent** — failed runs, avg tool calls per run

## MVP Alerting Assumptions

| Alert | Condition | Channel |
|-------|-----------|---------|
| API down | Health check fails 3x | Email/Slack (manual setup) |
| High 5xx | >5% over 5 min | Log-based metric alarm |
| Ingestion backlog | pending > 50 for 30 min | Optional |
| LLM errors | provider 5xx spike | Log filter |

No PagerDuty integration in MVP.

## Debugging Playbook

| Symptom | Steps |
|---------|-------|
| Slow RAG | Check `rag_query_duration_seconds`; inspect retrieval count; verify LLM latency |
| Wrong answers | Inspect message metadata citations/scores; verify document indexed |
| Ingestion stuck | Check worker logs; Redis queue depth; job `error_message` |
| 403 unexpected | Audit log `failed_authorization`; verify role matrix |
| High cost | Admin usage API; filter `usage_events` by workspace/day |
| Cross-tenant suspicion | Run isolation integration tests; grep logs for workspace_id mismatch |

## Tracing-Ready Architecture

- Request ID correlates API → worker → usage logs
- No OpenTelemetry in MVP; headers structured for future addition

## What Should Be Logged (Summary)

| Event | Level | Fields |
|-------|-------|--------|
| HTTP request complete | info | request_id, status, duration, user, workspace |
| Auth failure | warn | request_id, reason (no password) |
| Ingestion start/complete/fail | info/error | job_id, document_id, workspace_id |
| LLM/embedding call | info | tokens, cost, latency, workspace_id |
| Agent tool execution | info | tool_name, run_id, status |
| Permission denied | warn | user_id, workspace_id, action |
| Unhandled exception | error | request_id, stack trace |

Never log: passwords, JWT tokens, full document content, API keys.
