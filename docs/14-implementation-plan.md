# Implementation Plan

Phased engineering plan aligned to MVP backlog (79 stories). Each phase has exit criteria before proceeding.

## Phase Overview

```text
Phase 1: Foundation     → Auth, workspaces, infra, observability baseline
Phase 2: Documents      → Upload, storage, ingestion pipeline
Phase 3: Retrieval+RAG  → Vector search, Q&A, conversations
Phase 4: Agent          → Incident agent, tools, structured output
Phase 5: Admin+Audit    → Usage, dashboard APIs, audit logs
Phase 6: Deploy+Demo    → CI, Terraform, seed data, polish
```

---

## Phase 1: Foundation

**Objective:** Runnable local stack with auth, workspaces, RBAC, and production baseline.

### Included stories

| Prefix | Stories |
|--------|---------|
| AUTH | AUTH-001 – AUTH-006 |
| WS | WS-001 – WS-007 |
| OBS | OBS-001 – OBS-004 |
| INFRA | INFRA-001 – INFRA-003 |

### Technical tasks

- Docker Compose: postgres+pgvector, redis, api skeleton
- FastAPI app factory, Alembic init, SQLAlchemy models for users/workspaces/members
- JWT auth, bcrypt, middleware, `PermissionService`
- Workspace CRUD + membership APIs
- Structured logging, request ID middleware, standard errors, `/health`
- Repository base class requiring `workspace_id`

### Dependencies

None.

### Exit criteria

- [ ] Register, login, create workspace, invite member with role
- [ ] Viewer blocked from upload (403)
- [ ] Cross-workspace access returns 403/404
- [ ] `docker compose up` + migrations succeed
- [ ] Health check passes

### Risks

- JWT secret misconfiguration — document in `.env.example`
- Permission matrix drift — unit test matrix in same PR as routes

---

## Phase 2: Documents & Ingestion

**Objective:** Upload → async index → searchable chunks in pgvector.

### Included stories

| Prefix | Stories |
|--------|---------|
| DOC | DOC-001 – DOC-007 |
| ING | ING-001 – ING-007 |
| USAGE | USAGE-002 (embedding logs) |
| OBS | OBS-005, OBS-007 |

### Technical tasks

- Storage abstraction (local + S3 stub)
- Document APIs: upload, list, get, delete, re-index
- `documents`, `document_chunks`, `ingestion_jobs` models
- Celery app + `process_ingestion_job` task
- Extractors, chunker, embedding provider integration
- pgvector index + workspace-scoped chunk insert
- Job status tracking, retry, failure handling
- Log embedding usage events

### Dependencies

Phase 1 complete.

### Exit criteria

- [ ] Upload PDF/MD/TXT/JSON → job completes → document `indexed`
- [ ] Failed ingestion sets `failed` with error visible via API
- [ ] Re-index replaces chunks
- [ ] Delete removes chunks and storage file
- [ ] Worker processes jobs with `task_always_eager` in tests

### Risks

- PDF extraction quality — test fixtures for common cases
- pgvector index build time — acceptable for demo corpus size

---

## Phase 3: Retrieval & RAG

**Objective:** Grounded Q&A with citations and conversation history.

### Included stories

| Prefix | Stories |
|--------|---------|
| RET | RET-001 – RET-005 |
| RAG | RAG-001 – RAG-007 |
| USAGE | USAGE-001 (LLM logs) |

### Technical tasks

- `RetrievalService`: embed query, vector search, filters, scores
- `RagQueryService`: prompt builder, LLM provider, citation mapper
- Insufficient context path (no LLM hallucination)
- `conversations`, `messages` models and APIs
- Multi-turn with bounded history
- Log chat completion usage
- Integration tests for isolation and citations

### Dependencies

Phase 2 (indexed documents exist).

### Exit criteria

- [ ] Seeded workspace answers incident question with citations
- [ ] Empty workspace returns insufficient context
- [ ] Vector search never returns other workspace chunks (test)
- [ ] Conversation follow-up works
- [ ] Usage events recorded per query

### Risks

- Retrieval threshold tuning — expose via env var
- LLM cost during dev — use mini models, mock in CI

---

## Phase 4: Agent Investigation

**Objective:** Safe multi-step agent with tool registry and structured output.

### Included stories

| Prefix | Stories |
|--------|---------|
| AGENT | AGENT-001 – AGENT-009 |

### Technical tasks

- Tool registry + executor (5 tools)
- `AgentOrchestrator` loop with max steps and timeout
- `agent_runs`, `agent_tool_calls` models and APIs
- Structured Pydantic final summary
- Tool call logging and citation aggregation
- Agent audit events

### Dependencies

Phase 3 (retrieval + LLM abstraction shared).

### Exit criteria

- [ ] Agent run completes for billing/502 demo objective
- [ ] Tool calls logged and listable
- [ ] Unsupported tool rejected
- [ ] Foreign document ID rejected in tools
- [ ] Structured JSON result validates against schema

### Risks

- Runaway token usage — enforce step and timeout limits early
- Non-deterministic agent paths — demo with seeded docs and fixed mock in CI

---

## Phase 5: Admin, Usage & Audit

**Objective:** Visibility for owners/admins — usage, jobs, audit trail.

### Included stories

| Prefix | Stories |
|--------|---------|
| USAGE | USAGE-003, USAGE-004 |
| ADMIN | ADMIN-001 – ADMIN-005 |
| AUDIT | AUDIT-001 – AUDIT-007 |
| OBS | OBS-006 |

### Technical tasks

- Cost estimation table and `UsageService.get_workspace_summary`
- Admin aggregation endpoints
- Audit service wired to document, role, auth, agent events
- Prometheus `/metrics` endpoint
- Failed jobs widget data

### Dependencies

Phases 2–4 generating events.

### Exit criteria

- [x] Admin usage shows token and cost totals (USAGE-003/004 API; UI in ADMIN-004)
- [x] Admin dashboard aggregates: documents-overview, ingestion-jobs, recent-questions, failed-jobs (ADMIN-BATCH-002)
- [ ] Audit log query returns upload/delete/role change events
- [x] Viewer blocked from admin endpoints (USAGE-004 `/admin/usage` + ADMIN-BATCH-002)
- [ ] Metrics endpoint exposes required counters

### Risks

- Audit volume — pagination required from day one

---

## Phase 6: Deploy, CI & Demo Readiness

**Objective:** Portfolio-ready demo with CI, Terraform scaffold, seed data, docs.

### Included stories

| Prefix | Stories |
|--------|---------|
| INFRA | INFRA-004 – INFRA-008 |

### Technical tasks

- Northstar Cloud seed script
- GitHub Actions CI (lint, test, build)
- Terraform scaffold for AWS ECS/RDS/Redis/S3
- README with architecture link to `docs/`
- OpenAPI polish
- Optional minimal Next.js or Swagger-only demo UI
- Smoke test script
- Security isolation test suite green

### Dependencies

Phases 1–5 feature complete.

### Exit criteria

- [ ] CI green on main
- [ ] Demo script: register → workspace → seed → query → agent → admin usage
- [ ] Terraform plan succeeds (no manual console steps documented)
- [ ] Architecture docs linked from README (INFRA-007)

### Risks

- Cloud deploy cost — keep Fargate count at 1+1
- Demo LLM keys — use env secrets in GitHub Actions for optional e2e

---

## Story Mapping Summary

| Phase | Epic coverage |
|-------|---------------|
| 1 | AUTH, WS, OBS (partial), INFRA (partial) |
| 2 | DOC, ING, USAGE (embed), OBS (partial) |
| 3 | RET, RAG, USAGE (LLM) |
| 4 | AGENT |
| 5 | USAGE, ADMIN, AUDIT, OBS (metrics) |
| 6 | INFRA (remainder) |

## Recommended Team Sequence

Single developer: strict phase order 1 → 6.

Two developers after Phase 1:
- Dev A: Phase 2 → 3
- Dev B: OBS/INFRA hardening + admin prep
- Merge at Phase 3 exit before agent work

## Deferred Explicitly

- Streaming responses
- Hybrid search / reranker
- Dedicated vector DB
- SSO, billing, external integrations
- JWT blocklist (P1 within auth)
- Frontend polish beyond demo needs

## Major Tradeoffs Accepted

| Tradeoff | Rationale |
|----------|-----------|
| pgvector vs Pinecone | Simpler ops; sufficient for MVP corpus |
| Sync agent vs async | Simpler client; 120s timeout acceptable for demo |
| Modular monolith | Faster delivery; clear module splits |
| ECS vs Cloud Run | AWS ecosystem for storage and RDS |
| Non-streaming RAG | Matches A9 assumption; simpler API |

## Definition of MVP Done

All Phase 6 exit criteria met, plus:

- 10 critical security tests passing (see [13-testing-strategy.md](./13-testing-strategy.md))
- No P0 stories open
- Architecture ADRs accepted in `docs/adr/`
