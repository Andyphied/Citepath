# AtlasOps AI — Architecture Documentation

Architecture package for the **AtlasOps AI MVP**. These documents translate the [MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md) and [PRD](../PRD.md) into an implementation-ready technical design.

## Purpose

This package defines:

- System boundaries and component responsibilities
- Data model, APIs, and module structure
- RAG and agent execution flows with grounding and safety constraints
- Security, tenancy isolation, and RBAC
- Ingestion pipeline, observability, deployment, and testing
- Architecture Decision Records (ADRs) for key tradeoffs

It does **not** duplicate product requirements or expand MVP scope beyond the 79 user stories in [`stories/`](../stories/README.md).

## How to Read These Docs

0. New reviewers: start with the root [README.md](../README.md) for a under-30-min local demo path (real LLM key → Compose → sync seed → JWT → query), env vars, security/isolation notes, and design tradeoffs.
1. Start with [01-system-overview.md](./01-system-overview.md) for the MVP loop and non-goals.
2. Read [02-architecture-diagram.md](./02-architecture-diagram.md) and [03-container-diagram.md](./03-container-diagram.md) for visual context.
3. Implement backend structure from [04-module-boundaries.md](./04-module-boundaries.md) and [05-data-model.md](./05-data-model.md).
4. Build APIs per [06-api-design.md](./06-api-design.md).
5. Implement AI paths via [07-rag-architecture.md](./07-rag-architecture.md) and [08-agent-architecture.md](./08-agent-architecture.md).
6. Enforce security per [09-security-and-rbac.md](./09-security-and-rbac.md).
7. Wire async ingestion per [10-ingestion-pipeline.md](./10-ingestion-pipeline.md).
8. Add production concerns from [11-observability.md](./11-observability.md) and [12-deployment-architecture.md](./12-deployment-architecture.md).
9. Validate with [13-testing-strategy.md](./13-testing-strategy.md).
10. Execute in order per [14-implementation-plan.md](./14-implementation-plan.md).
11. Consult [adr/](./adr/) when making implementation choices.

## MVP Architecture Summary

| Layer | Choice |
|-------|--------|
| Backend | Python 3.11+, FastAPI, modular monolith |
| Database | PostgreSQL 16 + pgvector |
| Queue / cache | Redis 7 + Celery |
| Object storage | Local filesystem (dev) / S3 (cloud) |
| LLM | OpenAI or Anthropic via provider abstraction |
| Frontend | Minimal Next.js or Swagger-first demo |
| Deploy | Docker Compose (local), AWS ECS Fargate (cloud) |

**Core product loop:**

```text
workspace → document upload → ingestion → vector search → grounded answer → agent investigation → usage visibility
```

**Tenancy:** Every tenant-owned record includes `workspace_id`. Authorization runs at middleware, service, and repository layers.

**Sync vs async:** Upload and query/agent API calls are synchronous (non-streaming). Ingestion (extract → chunk → embed → persist) runs in Celery workers.

## Document Index

| Doc | Description |
|-----|-------------|
| [01-system-overview.md](./01-system-overview.md) | Product summary, capabilities, risks |
| [02-architecture-diagram.md](./02-architecture-diagram.md) | System context diagram and narrative |
| [03-container-diagram.md](./03-container-diagram.md) | C4-style container view |
| [04-module-boundaries.md](./04-module-boundaries.md) | Backend modules and folder structure |
| [05-data-model.md](./05-data-model.md) | Tables, indexes, ERD |
| [06-api-design.md](./06-api-design.md) | REST endpoints and contracts |
| [07-rag-architecture.md](./07-rag-architecture.md) | Retrieval, grounding, citations |
| [08-agent-architecture.md](./08-agent-architecture.md) | Incident agent, tools, guardrails |
| [09-security-and-rbac.md](./09-security-and-rbac.md) | Auth, roles, isolation |
| [10-ingestion-pipeline.md](./10-ingestion-pipeline.md) | Upload through indexing |
| [11-observability.md](./11-observability.md) | Logs, metrics, health, debugging |
| [12-deployment-architecture.md](./12-deployment-architecture.md) | Local and AWS deployment |
| [13-testing-strategy.md](./13-testing-strategy.md) | Test types and critical cases |
| [14-implementation-plan.md](./14-implementation-plan.md) | Phased engineering plan |

## Diagrams

| File | Description |
|------|-------------|
| [diagrams/system-context.mmd](./diagrams/system-context.mmd) | External actors and system boundary |
| [diagrams/container-diagram.mmd](./diagrams/container-diagram.mmd) | Containers and dependencies |
| [diagrams/ingestion-flow.mmd](./diagrams/ingestion-flow.mmd) | Document ingestion pipeline |
| [diagrams/rag-query-flow.mmd](./diagrams/rag-query-flow.mmd) | RAG question answering |
| [diagrams/agent-run-flow.mmd](./diagrams/agent-run-flow.mmd) | Agent investigation lifecycle |
| [diagrams/auth-rbac-flow.mmd](./diagrams/auth-rbac-flow.mmd) | Auth and permission checks |
| [diagrams/deployment-diagram.mmd](./diagrams/deployment-diagram.mmd) | Local and cloud topology |

## Architecture Decision Records

| ADR | Title |
|-----|-------|
| [ADR-001](./adr/ADR-001-backend-architecture-style.md) | Backend architecture style (modular monolith + FastAPI) |
| [ADR-002](./adr/ADR-002-vector-store-choice.md) | Vector store (PostgreSQL + pgvector) |
| [ADR-003](./adr/ADR-003-llm-provider-abstraction.md) | LLM provider abstraction |
| [ADR-004](./adr/ADR-004-background-job-processing.md) | Background job processing (Redis + Celery) |
| [ADR-005](./adr/ADR-005-workspace-isolation-model.md) | Workspace isolation model |
| [ADR-006](./adr/ADR-006-agent-tool-execution-model.md) | Agent tool execution model |
| [ADR-007](./adr/ADR-007-token-usage-and-cost-tracking.md) | Token usage and cost tracking |
| [ADR-008](./adr/ADR-008-deployment-target.md) | Deployment target (AWS ECS Fargate) |

## Deferred (Post-MVP)

Explicitly out of scope for this architecture package:

- Slack/GitHub/Notion integrations
- SSO, enterprise billing, multi-region
- Streaming responses, hybrid search reranking service
- Dedicated vector DB migration (designed for, not implemented)
- Kubernetes, service mesh, event sourcing, CQRS
