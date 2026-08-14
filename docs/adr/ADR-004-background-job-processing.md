# ADR-004: Background Job Processing

## Status

Accepted

## Context

Document ingestion (extract, chunk, embed, persist) takes seconds to minutes — unsuitable for synchronous HTTP. MVP assumption A5 specifies Redis + Celery or RQ with one worker. Re-index and retry flows also require durable background execution.

## Decision

Use **Redis 7 as message broker** and **Celery 5** for background task processing.

Primary task: `process_ingestion_job(job_id: UUID)`.

Configuration:
- `task_acks_late=True`
- `autoretry_for` transient errors, max 3 retries, exponential backoff
- `task_time_limit=600` (10 min hard limit per job)
- Disable Celery result backend; job status in PostgreSQL `ingestion_jobs`

## Consequences

**Positive:**
- Mature Python ecosystem integration with FastAPI
- Retries, visibility, and rate control well documented
- Same Redis instance usable for JWT blocklist cache (optional)
- Local dev parity: worker container in Docker Compose

**Negative:**
- Celery operational concepts (workers, broker) vs simpler RQ
- Must ensure tasks are idempotent (job status checks on entry)
- Worker must be deployed separately in ECS

## Alternatives Considered

| Alternative | Why not selected |
|-------------|------------------|
| **Synchronous ingestion** | Blocks HTTP; poor UX for PDFs; violates ING stories |
| **RQ (Redis Queue)** | Simpler but less feature-rich retries and monitoring; Celery preferred for production-style job processing |
| **Serverless queues (SQS + Lambda)** | Split runtime from monolith; cold start; local dev friction |
| **Kafka** | Massive ops overhead for single ingestion queue |
| **Cron-based polling** | Higher latency, poor retry semantics, wastes DB polls |

## Implementation Notes

- Pass `workspace_id` and `job_id` to task; re-validate document ownership at worker start
- Use `celery -A app.infrastructure.celery_app worker -l info -c 2` in worker container
- Tests: `task_always_eager=True` routes tasks synchronously
- Enqueue after DB commit to avoid race on missing job row
- Health check: verify Redis connectivity and optionally queue depth
