# Module Boundaries

Backend structure for the **modular monolith**. Each module owns domain logic for its area. Cross-module calls go through explicit service interfaces, not direct ORM access across boundaries.

## Suggested Folder Structure

```text
app/
  main.py                    # FastAPI app factory
  api/
    deps.py                  # Depends: current_user, workspace_context
    routes/
      auth.py
      workspaces.py
      documents.py
      queries.py
      conversations.py
      agent_runs.py
      admin.py
      health.py
  modules/
    auth/
      models.py
      schemas.py
      service.py
      repository.py
    users/
      ...
    workspaces/
      ...
    documents/
      ...
    ingestion/
      tasks.py               # Celery tasks
      pipeline.py
      extractors/
      chunker.py
    retrieval/
      embedder.py
      search.py
    rag/
      prompt_builder.py
      query_service.py
      citation_mapper.py
    agents/
      orchestrator.py
      tool_registry.py
      tools/
    usage/
      service.py
      cost_calculator.py
    audit/
      service.py
    admin/
      aggregations.py
    observability/
      logging.py
      metrics.py
      middleware.py
  infrastructure/
    db/
      session.py
      base.py
    storage/
      interface.py
      local.py
      s3.py
    llm/
      interface.py
      openai_provider.py
      anthropic_provider.py
    celery_app.py
    config.py
  migrations/                # Alembic
tests/
  unit/
  integration/
  security/
```

## Module Definitions

### `auth`

| Aspect | Detail |
|--------|--------|
| **Responsibility** | Registration, login, logout, JWT issue/validate, password hashing |
| **Owns** | `users` (credentials subset), JWT config, optional token blocklist |
| **Exposes** | `AuthService.register/login/logout`, `get_current_user` dependency |
| **Depends on** | `users`, `infrastructure` |
| **Must NOT depend on** | `documents`, `rag`, `agents`, `workspaces` (except via user id) |

**Notes:** Use bcrypt (cost factor 12). JWT claims: `sub` (user id), `exp`, `iat`. Email normalized to lowercase.

---

### `users`

| Aspect | Detail |
|--------|--------|
| **Responsibility** | User profile CRUD (non-auth fields) |
| **Owns** | `users` entity |
| **Exposes** | `UserService.get_by_id`, profile fields |
| **Depends on** | `infrastructure` |
| **Must NOT depend on** | `workspaces`, `rag`, `agents` |

---

### `workspaces`

| Aspect | Detail |
|--------|--------|
| **Responsibility** | Workspace CRUD, membership, roles, permission checks |
| **Owns** | `workspaces`, `workspace_members` |
| **Exposes** | `WorkspaceService`, `PermissionService.require(role, action)`, `WorkspaceContext` |
| **Depends on** | `users`, `audit` |
| **Must NOT depend on** | `rag`, `agents`, `ingestion` internals |

**Notes:** `PermissionService` centralizes WS-005 matrix. Last Owner cannot be removed.

---

### `documents`

| Aspect | Detail |
|--------|--------|
| **Responsibility** | Upload metadata, list/get/delete, trigger re-index, status |
| **Owns** | `documents` |
| **Exposes** | `DocumentService.upload/list/get/delete/reindex` |
| **Depends on** | `workspaces`, `ingestion` (enqueue only), `infrastructure.storage`, `audit` |
| **Must NOT depend on** | `rag`, `agents` directly |

**Notes:** Upload returns after file stored + job created. Supported types: `.pdf`, `.md`, `.txt`, `.json`. Max size configurable (default 20 MB).

---

### `ingestion`

| Aspect | Detail |
|--------|--------|
| **Responsibility** | Job lifecycle, text extraction, chunking, embedding persistence |
| **Owns** | `ingestion_jobs`, chunk write path |
| **Exposes** | `IngestionService.enqueue`, `IngestionPipeline.run`, Celery tasks |
| **Depends on** | `documents`, `retrieval` (embedder), `usage`, `audit`, `infrastructure` |
| **Must NOT depend on** | `rag`, `agents`, HTTP route handlers |

**Notes:** Pipeline is idempotent per `(document_id, job_id)`. On re-index, delete chunks for document then re-ingest.

---

### `retrieval`

| Aspect | Detail |
|--------|--------|
| **Responsibility** | Query embedding, workspace-scoped vector search, metadata filters, scores |
| **Owns** | Read access to `document_chunks` |
| **Exposes** | `RetrievalService.search(query, workspace_id, filters, top_k)` |
| **Depends on** | `infrastructure.llm` (embeddings), `infrastructure.db` |
| **Must NOT depend on** | `rag`, `agents`, `api` |

**Notes:** Default `top_k=8`. Minimum similarity threshold configurable (default 0.72 cosine). Every SQL/query includes `workspace_id`.

---

### `rag`

| Aspect | Detail |
|--------|--------|
| **Responsibility** | RAG orchestration: retrieve → prompt → LLM → citations → conversation storage |
| **Owns** | `conversations`, `messages` (RAG mode) |
| **Exposes** | `RagQueryService.ask(question, workspace_id, conversation_id?)` |
| **Depends on** | `retrieval`, `workspaces`, `usage`, `infrastructure.llm` |
| **Must NOT depend on** | `agents`, Celery tasks |

**Notes:** Insufficient context when zero chunks or all scores below threshold — no fabricated answers.

---

### `agents`

| Aspect | Detail |
|--------|--------|
| **Responsibility** | Incident investigation agent loop, tool registry, structured output |
| **Owns** | `agent_runs`, `agent_tool_calls` |
| **Exposes** | `AgentService.start_investigation(objective, workspace_id)` |
| **Depends on** | `retrieval`, `documents`, `rag` (shared prompt/citation utilities), `usage`, `audit`, `infrastructure.llm` |
| **Must NOT depend on** | Raw HTTP layer |

**Notes:** Max 8 tool steps, 120s wall clock. Tools are read-only and workspace-scoped.

---

### `usage`

| Aspect | Detail |
|--------|--------|
| **Responsibility** | Log all LLM/embedding calls, cost estimation, workspace summaries |
| **Owns** | `usage_events` |
| **Exposes** | `UsageService.log_event`, `UsageService.get_workspace_summary` |
| **Depends on** | `infrastructure` |
| **Must NOT depend on** | Business logic modules (called by them) |

**Notes:** Called synchronously after each provider call. Never fail user request if usage log fails — log error and continue.

---

### `audit`

| Aspect | Detail |
|--------|--------|
| **Responsibility** | Append-only security and admin audit events |
| **Owns** | `audit_logs` |
| **Exposes** | `AuditRepository.create`, `AuditService.list_logs` |
| **Depends on** | `infrastructure` |
| **Must NOT depend on** | `rag`, `agents` |

**Events:** `document.uploaded`, `document.deleted`, `document.reindex_requested`, `member.role_changed`, `failed_authorization`, `agent.run_completed`.

---

### `admin`

| Aspect | Detail |
|--------|--------|
| **Responsibility** | Read-only aggregations for dashboard |
| **Owns** | None (query-only) |
| **Exposes** | Admin HTTP routes for `usage`, `audit-logs`, `documents-overview`, `ingestion-jobs`, `recent-questions`, `failed-jobs` |
| **Depends on** | `documents`, `ingestion`, `rag`, `usage`, `audit`, `workspaces` |
| **Must NOT depend on** | LLM providers directly |

**Notes:** All endpoints require Owner or Admin role.

---

### `observability`

| Aspect | Detail |
|--------|--------|
| **Responsibility** | Structured logging, request IDs, metrics, error format, health checks |
| **Owns** | None |
| **Exposes** | Middleware, `GET /health`, `GET /metrics` |
| **Depends on** | `infrastructure` |
| **Must NOT depend on** | Domain modules |

---

### `infrastructure`

| Aspect | Detail |
|--------|--------|
| **Responsibility** | DB sessions, config, storage adapters, LLM clients, Celery app |
| **Owns** | Connection pools, env config |
| **Exposes** | `get_db`, `Settings`, `StorageBackend`, `LLMProvider`, `EmbeddingProvider` |
| **Depends on** | External libraries only |
| **Must NOT depend on** | Any `modules/*` domain code |

## Dependency Rules (Summary)

```text
api/routes → modules/* → infrastructure
modules/agents → modules/retrieval, modules/documents
modules/rag → modules/retrieval
modules/ingestion → modules/retrieval (embeddings only)
modules/* → modules/workspaces (permissions)
modules/* → modules/usage, modules/audit (side effects)
```

**Forbidden:** `infrastructure` importing `modules`. `retrieval` importing `rag`. Circular imports between `documents` and `ingestion` — use interface/event enqueue only.

## Workspace Context Propagation

Every service method that touches tenant data accepts `WorkspaceContext`:

```python
@dataclass
class WorkspaceContext:
    workspace_id: UUID
    user_id: UUID
    role: WorkspaceRole
```

Repositories reject calls missing `workspace_id`.
