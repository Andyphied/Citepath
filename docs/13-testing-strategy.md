# Testing Strategy

Test approach for AtlasOps AI MVP. Goal: prove **workspace isolation**, **grounded AI behavior**, and **core product loop** reliability.

## Test Pyramid

```text
        /\
       /  \  Smoke (deployed env)
      /----\
     / API  \  Integration + API tests
    /--------\
   /  Unit    \  Domain logic, permissions, chunking
  /--------------\
```

## Test Types

### Unit Tests

**Scope:** Pure functions and services with mocked dependencies.

| Area | Examples |
|------|----------|
| `PermissionService` | Full role matrix permutations |
| Chunker | Token counts, overlap, heading preservation |
| Citation mapper | Valid/invalid chunk ID handling |
| Cost calculator | Token → USD estimates |
| Tool registry | Unknown tool rejection |
| Prompt builder | Chunk boundary formatting |

**Location:** `tests/unit/`

### Integration Tests

**Scope:** Real PostgreSQL (+ pgvector) and Redis in test containers.

| Area | Examples |
|------|----------|
| Repositories | CRUD with workspace_id filtering |
| Ingestion pipeline | Extract → chunk → embed (mock provider) → persist |
| Retrieval | Vector search returns only same-workspace chunks |
| RAG service | End-to-end with mocked LLM |
| Agent orchestrator | Multi-step with mocked LLM tool calls |

**Location:** `tests/integration/`

Fixtures: pytest + `testcontainers` or GitHub Actions service containers.

### API Tests

**Scope:** HTTP layer via `TestClient` / `httpx.AsyncClient`.

- Auth flows: register, login, me, expired token
- Workspace CRUD and membership
- Document upload (multipart with sample files)
- Query endpoint response shape
- Admin endpoints 403 for Viewer

**Location:** `tests/api/`

### Ingestion Tests

- PDF, MD, TXT, JSON sample files in `tests/fixtures/documents/`
- Job status transitions pending → completed
- Failed extraction sets `failed` status and error_message
- Re-index replaces chunks (count stable, content updated)

### RAG Tests

- Mock LLM returns deterministic answer
- Citations present when chunks retrieved
- Insufficient context path: no chunks → `insufficient_context: true`
- Scores below threshold → same behavior
- Conversation continuity stores messages

### Agent Tool Tests

Each tool in isolation with seeded workspace data:
- `search_knowledge_base` — returns citations
- `summarize_document` — wrong workspace doc → error
- `extract_action_items`, `compare_incidents`, `suggest_debugging_steps`

Orchestrator test: max steps respected; unsupported tool rejected.

### RBAC / Security Tests

**Critical — dedicated file `tests/security/`:**

| Test case | Expected |
|-----------|----------|
| Viewer uploads document | 403 |
| Member deletes document | 204 |
| Admin views audit logs | 200 |
| Viewer views audit logs | 403 |
| Non-member accesses workspace | 403 |
| User A gets User B's document by UUID | 404 |

### Workspace Isolation Tests

**Critical — highest priority:**

```python
def test_user_cannot_access_other_workspace_document(...)
def test_vector_search_workspace_scoped(...)
def test_agent_tool_rejects_foreign_document_id(...)
def test_conversation_not_visible_across_users(...)
```

Seed two workspaces with distinct chunks; verify zero cross-retrieval.

### Migration Tests

- Run all Alembic migrations from empty DB in CI
- Verify pgvector extension and indexes exist
- Optional: downgrade one revision and re-upgrade

### Frontend Tests (web/)

Minimal Next.js scaffold tests live under `web/` (Vitest + Testing Library):

| Area | Examples |
|------|----------|
| API client | Bearer injection, structured `ApiError`, network failure, FormData without forced `Content-Type` |
| Auth gate helpers | Cookie presence, protected-path classification, post-auth `next` sanitize |
| Auth client helpers | Login/register/me/logout request shapes and error mapping |
| Workspace context | Active workspace resolution, `/workspaces/{id}/...` paths |
| Documents helpers | List query params, multipart upload shape, status badge tones, upload role gate |
| Ask / RAG helpers | Query POST body + conversation_id, `?q=` prefill, citation location labels, safe markdown, thread append |
| Agent helpers | Agent-run POST body, 120s client timeout → `agent_timeout`, InvestigationSummary section mapping, workspace stale-response guard |
| Admin helpers | Documents-overview / ingestion-jobs / failed-jobs / usage GET paths, Owner/Admin role gate + Admin nav `adminOnly`, cost/token format, workspace stale-response guard |

Run: `cd web && npm test`

### Smoke Tests

Post-deploy script against staging/production:
1. `GET /health` → ok
2. Login with demo user
3. List documents
4. POST query with known seeded question → citations non-empty

### Seed Data Tests

- `scripts/seed_demo.py` runs without error
- Northstar Cloud workspace has ≥ N indexed documents
- Sample question retrieves expected document title

## Minimum Coverage Expectations (MVP)

| Layer | Target |
|-------|--------|
| Overall line coverage | ≥ 70% |
| `workspaces` permissions | ≥ 95% |
| `retrieval` workspace filter | 100% branch on isolation paths |
| `rag` insufficient context | 100% of defined branches |
| `agents` tool registry | 100% rejection paths |

Coverage is a floor, not a goal — critical cases above are mandatory regardless of percentage.

## Critical Test Cases (Must Pass Before MVP Demo)

1. User cannot access another workspace's document
2. Vector search is workspace-scoped
3. RAG answer cites source chunks when context exists
4. Insufficient context returns safe fallback (no fabricated internals)
5. Ingestion failure is recorded with `failed` status and error_message
6. Agent cannot use unsupported tools
7. Usage is logged for LLM and embedding calls
8. Viewer cannot upload; can query
9. Audit log written on document delete and failed authorization
10. Re-index produces fresh chunks

## Mocking Strategy

| Dependency | Approach |
|------------|----------|
| OpenAI / Anthropic | `pytest` fixtures with recorded responses |
| S3 | Local storage backend in tests |
| Celery | `task_always_eager=True` for integration tests |
| Clock | Freezegun for token expiry tests |

## CI Configuration

GitHub Actions job:
- Spin up postgres:16 + pgvector, redis
- `alembic upgrade head`
- `pytest tests/ -v --cov=app --cov-fail-under=70`
- Fail PR on any security test failure

## Test Data Management

- Factory functions: `make_user`, `make_workspace`, `make_document`
- Each test creates isolated workspace unless explicitly testing cross-tenant
- Truncate tables or transactional rollback per test

## What Not to Test in MVP

- LLM answer quality (subjective) — manual demo validation only
- Terraform apply (plan only in CI)
- Load/stress testing
- Provider SDK internals

## Debugging Failed Tests

- Enable `LOG_LEVEL=DEBUG` in pytest
- Dump retrieval scores in RAG test failures
- Inspect `usage_events` and `agent_tool_calls` rows in integration failures
