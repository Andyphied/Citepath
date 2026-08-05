# System Overview

## Product Summary

AtlasOps AI is a multi-tenant AI knowledge assistant for engineering teams. Users create **workspaces**, upload technical documents (runbooks, incident reports, architecture notes), and the system indexes them via embeddings and vector search. Engineers ask natural-language questions and receive **grounded answers with citations**. An **incident investigation agent** uses safe, read-only tools to search the knowledge base, summarize documents, compare incidents, and suggest debugging steps.

## MVP Product Loop

```text
workspace → document upload → ingestion → vector search → grounded answer → agent investigation → usage visibility
```

**Success bar:** A user registers, creates a workspace, uploads demo documents, asks an incident question, receives cited answers, runs an agent investigation, and reviews ingestion status and token usage — with **no cross-workspace data leakage**.

## Core Users

| Persona | Primary actions |
|---------|-----------------|
| Workspace Owner | Create workspace, manage members, view usage, delete workspace |
| Admin | Upload/manage documents, monitor ingestion, view admin dashboard and audit logs |
| Member (Engineer) | Ask RAG questions, run agent investigations, upload documents |
| Viewer | Ask questions and run agent; read documents; no mutations |

## Core Capabilities (MVP)

1. **Authentication** — Email/password, JWT, bcrypt password hashing
2. **Workspaces & RBAC** — Four roles with enforced permission matrix
3. **Document management** — Upload PDF, MD, TXT, JSON; list, view, delete, re-index
4. **Ingestion pipeline** — Async extract → chunk → embed → store in pgvector
5. **Vector retrieval** — Workspace-scoped similarity search, metadata filters, top-k with scores
6. **RAG Q&A** — Grounded answers, citations, insufficient-context handling, conversation history
7. **Incident agent** — Controlled tool registry, structured output, tool call logging
8. **Usage tracking** — LLM and embedding events with cost estimates per workspace
9. **Admin visibility** — Documents, jobs, recent questions, usage, failed jobs
10. **Audit & observability** — Security events, structured logs, request IDs, health checks

## Non-Goals (MVP)

- Slack, GitHub, Notion/Confluence integrations
- SSO, enterprise billing, automatic remediation
- Fine-tuning, streaming responses, hybrid search service
- External agent actions (deploy, restart, ticket creation)
- Dedicated vector DB (pgvector only for MVP)
- Kubernetes, multi-region, event sourcing

## Architecture Style

**Modular monolith** — Single FastAPI deployable with clear domain modules (`auth`, `workspaces`, `documents`, `ingestion`, `retrieval`, `rag`, `agents`, `usage`, `audit`, `admin`, `observability`, `infrastructure`). One API process and one Celery worker process share the same codebase and database.

Rationale: MVP team size and traffic do not justify distributed services. Module boundaries allow future extraction without premature complexity.

## Major Components

| Component | Responsibility |
|-----------|----------------|
| Web App | Minimal Next.js or Swagger UI for demo |
| FastAPI API | REST endpoints, auth middleware, orchestration |
| Celery Worker | Document ingestion, embedding batches |
| PostgreSQL + pgvector | Relational data + vector similarity |
| Redis | Celery broker, optional JWT blocklist cache |
| Object storage | Raw uploaded files (local FS or S3) |
| LLM providers | OpenAI / Anthropic chat completions |
| Embedding provider | OpenAI embeddings (configurable) |

## Primary Data Flows

### 1. Document ingestion (async)

Upload → validate → store file → create document + ingestion job → enqueue worker → extract → chunk → embed → persist chunks → update statuses → log usage.

### 2. RAG query (sync)

Question → auth/workspace check → embed query → workspace-filtered vector search → build prompt → LLM → citations → persist messages → log usage → response.

### 3. Agent investigation (sync)

Objective → create agent run → plan/execute allowed tools (max 8 steps) → log each tool call → structured summary with citations → log usage/audit.

### 4. Admin visibility (sync)

Authenticated Owner/Admin → aggregate queries scoped to workspace → usage, jobs, audit logs.

## Sync vs Async

| Operation | Mode | Rationale |
|-----------|------|-----------|
| Auth, workspace CRUD | Sync | Fast DB operations |
| Document upload metadata | Sync | Returns immediately after file stored + job enqueued |
| Ingestion processing | **Async** | PDF extraction and embedding are slow |
| RAG query | Sync | Non-streaming MVP; single response |
| Agent run | Sync | Bounded loop (max 8 steps, 120s timeout) |
| Re-index | Async | Same pipeline as ingestion |

## Workspace Isolation

Isolation enforced at three layers:

1. **API middleware** — Validates JWT, loads membership, checks role
2. **Service layer** — Every operation receives `workspace_id` from authorized context, never from unchecked client input alone
3. **Repository layer** — All tenant queries include `WHERE workspace_id = :workspace_id`

Vector search **must** filter by `workspace_id` before ranking. Cross-workspace chunk IDs in citations are rejected.

## Key Architecture Risks

| Risk | Mitigation |
|------|------------|
| Cross-tenant data leakage | Mandatory `workspace_id` on all tenant tables; isolation integration tests |
| LLM hallucination | Grounded prompts only; insufficient-context path skips or strictly refuses |
| Runaway agent cost | Max steps (8), timeout (120s), tool registry whitelist |
| Ingestion failures | Retry with backoff; failed status + error message; admin visibility |
| pgvector scale limits | Acceptable for MVP demo corpus; ADR-002 defines migration trigger |
| JWT theft | HTTPS only in cloud; short expiry; optional Redis blocklist on logout |

## Answers to Key Questions

1. **Smallest credible architecture:** FastAPI monolith + Postgres/pgvector + Redis/Celery + S3/local storage + one LLM provider.
2. **Core components:** API, worker, DB, Redis, storage, LLM/embed APIs, minimal frontend.
3. **Sync vs async:** Queries and agents sync; ingestion async.
4. **Isolation:** Middleware + service + repository `workspace_id` filtering.
5. **Documents:** Multipart upload → storage → job → worker pipeline.
6. **Embeddings:** Batch via provider; stored in `document_chunks.embedding` (vector column).
7. **RAG:** Embed query → cosine similarity in pgvector → top-k → prompt → LLM.
8. **Citations:** Map LLM output to retrieved chunk IDs; return document title, chunk preview, score.
9. **Agent tools:** Whitelist registry; LLM selects from schema; executor validates before run.
10. **Unsafe actions:** No tools outside registry; no HTTP/file write/delete tools in MVP.
