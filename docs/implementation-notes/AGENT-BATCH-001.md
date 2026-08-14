# AGENT Batch 001 Implementation Note

## Summary

Delivered the Phase 4 agent core loop: start investigation API, JSON-planning orchestrator (max 8 steps, 120s timeout), whitelisted `search_knowledge_base` tool backed by `RetrievalService`, tool-call persistence, and structured investigation summary on completion.

## Stories Covered

| Story | Delivered |
|-------|-----------|
| AGENT-001 | `POST/GET /workspaces/{id}/agent-runs`, RBAC `RUN_AGENT`, `agent_runs` lifecycle |
| AGENT-002 | Orchestrator loop, tool registry/executor, tool-call logging |
| AGENT-003 | `search_knowledge_base` tool with optional filters |
| AGENT-008 | `InvestigationSummary` schema, persisted on `agent_runs.result` |

## Files Changed

| File | Purpose |
|------|---------|
| `app/modules/agents/service.py` | Investigation entrypoint; conversation_id validation; safe failure payloads |
| `app/modules/agents/orchestrator.py` | Plan → tool → summarize loop; zero-citation safe fallback |
| `app/modules/agents/tool_registry.py` | Static tool registry |
| `app/modules/agents/tool_executor.py` | Whitelist validation + sanitized failure outputs |
| `app/modules/agents/tools/search_knowledge_base.py` | Retrieval-backed search tool |
| `app/modules/agents/schemas.py` | Request/response/summary models |
| `app/modules/agents/repository.py` | Run updates + tool call persistence |
| `app/api/routes/agent_runs.py` | HTTP routes |
| `app/api/deps.py` | `AgentService` + `RequireRunAgentDep` + `RAGRepository` |
| `app/api/agent_errors.py` | Error handlers including orchestration failures |
| `app/main.py` | Registers agent exception handlers |
| `tests/unit/test_agent_*.py` | Executor, orchestrator, service, error handler tests |
| `tests/api/test_agent_runs.py` | API RBAC, isolation, orchestration failure tests |
| `tests/security/test_agent_workspace_isolation.py` | Foreign `document_id` isolation |

## Behavior Added

- Sync `POST /agent-runs` runs full investigation and returns structured summary + citations.
- Unknown tools rejected by executor before execution; attempt logged to `agent_tool_calls`.
- Agent LLM steps logged with `UsageOperation.AGENT_STEP`.
- Optional `conversation_id` must belong to the active workspace and calling user.
- Empty-citation runs return a safe structured fallback (no fabricated causes/checks).
- `related_documents` constrained to citation document IDs only.
- Tool/orchestration failures persist and return stable codes without raw exception text.

## Tests Added

- Unit: unknown tool rejection + logging, sanitized tool failures, orchestrator search-before-summary, zero-citation fallback, related_documents filter, conversation validation, orchestration error handler
- API (Docker): billing 502 objective; Viewer POST/GET allowed; non-member 403; unauthenticated 401; cross-workspace GET 404; foreign conversation_id 404; unknown-tool → 503
- Security (Docker): foreign `document_id` via `search_knowledge_base` → zero chunks

## Decisions Made

### Review fix cycle

1. **`AgentOrchestrationError` → HTTP 503** with stable `code=agent_orchestration_failed` and generic message (no internal detail). Registered in `main.py` alongside other agent handlers.
2. **Tool failure sanitization:** persist/return only `{"error":"invalid_arguments"}` / `{"error":"execution_failed"}` / `{"error":"unknown_tool"}` — never `str(exc)` or Pydantic `exc.errors()`.
3. **Zero-citation path skips summary LLM** and returns `build_insufficient_context_summary()` so free-form fabrication cannot occur.
4. **`conversation_id` validation** reuses `ConversationNotFoundError` (404) with the same ownership rules as RAG (`workspace_id` + `user_id`).
5. **Failed run `result` payloads** store stable codes (`agent_orchestration_failed` / `agent_completion_failed`) instead of raw exception strings.

## Known Limitations

- ADR-006 delimiter wrapping for tool observations not yet applied (deferred; non-blocking).
- Unknown-tool attempts are logged to `agent_tool_calls` then fail the run (no soft-continue retry).
- API/security Docker tests require local Docker + pgvector container.

## Follow-up Items

- **AGENT-004→007:** Register remaining tools in registry
- **AGENT-009:** `GET .../tool-calls` list API
- **AUDIT-006:** Agent run audit events
- **ADR-006:** Delimiter wrapping for tool observations (deferred; non-blocking)

## Platform follow-up

### CI coverage (no workflow change)

`.github/workflows/ci.yml` already covers agent suites via directory globs (same pattern as INFRA-005 / RAG-007):

| Job | Command | Agent coverage |
|-----|---------|----------------|
| `unit-tests` | `pytest tests/unit -q` | `tests/unit/test_agent_*.py` (errors, orchestrator, service, tool_executor) |
| `integration-tests` | `pytest tests/api tests/integration tests/security -q` | `tests/api/test_agent_runs.py`, `tests/security/test_agent_workspace_isolation.py` |

No new CI job or compose service required. README Tests section notes that agent suites are included in those globs and skip without Docker.

### Unblocked Docker-gated tests (Alembic revision length)

**Issue:** Fresh testcontainers failed during `alembic upgrade head` with:

`StringDataRightTruncation: value too long for type character varying(32)`

when writing revision `003_add_embedding_usage_operations` (34 chars) into `alembic_version.version_num`.

**Fix:** Shorten revision id to `003_embedding_usage_ops` (≤32) and point `004_add_document_filter_indexes.down_revision` at it. Filename unchanged.

**Local note:** Environments that never successfully stamped past `002` are fine (fresh CI/testcontainers). If a local DB was left mid-failure on the old id string, recreate the volume or `alembic stamp` after pull.

### Verification results

| Suite | Result |
|-------|--------|
| `pytest tests/unit/test_agent_*.py -q` | **12 passed** |
| `pytest tests/api/test_agent_runs.py tests/security/test_agent_workspace_isolation.py -v` (Docker / testcontainers) | **8 passed** |

### Observed (deferred)

- SAWarning cartesian product in `AgentRepository` tool-call count/list queries (`agent_runs` × `agent_tool_calls`) — product fix if desired; tests still pass.
