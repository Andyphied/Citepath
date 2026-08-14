# AGENT-BATCH-002 Implementation Note

## Summary

Registered and implemented the four remaining MVP agent tools — `summarize_document`, `extract_action_items`, `compare_incidents`, and `suggest_debugging_steps` — on top of the AGENT-BATCH-001 orchestrator, registry, and ToolExecutor patterns. All tools are workspace-scoped, read-only, citation-bearing, and log LLM usage via `UsageOperation.AGENT_STEP`.

## Stories Covered

| Story | Delivered |
|-------|-----------|
| AGENT-004 | `summarize_document(document_id)` with token-capped chunk loading, optional batch merge, citations |
| AGENT-005 | `extract_action_items(document_id)` with structured JSON action items + source chunk refs |
| AGENT-006 | `compare_incidents(document_ids[])` for 2–5 same-workspace docs; similarities/differences/themes |
| AGENT-007 | `suggest_debugging_steps(service_name, symptom)` searches KB then grounds checklist; labels speculative steps |

## Files Changed

| File | Purpose |
|------|---------|
| `app/modules/agents/tool_registry.py` | Registers all five MVP tools |
| `app/modules/agents/tool_executor.py` | Passes `agent_run_id` into handlers for usage metadata |
| `app/modules/agents/schemas.py` | Args models for the four new tools |
| `app/modules/agents/document_loader.py` | Workspace-scoped document/chunk load + safe failure codes |
| `app/modules/agents/token_budget.py` | tiktoken budget helpers for tool input caps |
| `app/modules/agents/tools/summarize_document.py` | Summarize tool |
| `app/modules/agents/tools/extract_action_items.py` | Action-item extraction tool |
| `app/modules/agents/tools/compare_incidents.py` | Multi-document compare tool |
| `app/modules/agents/tools/suggest_debugging_steps.py` | Grounded debugging checklist tool |
| `app/modules/agents/service.py` / `app/api/deps.py` | Wire document + ingestion repos into registry |
| `app/modules/agents/orchestrator.py` | Planning prompt mentions new tools |
| `docs/08-agent-architecture.md` | `compare_incidents` arity 2–5 |
| `tests/unit/test_agent_tools_batch_002.py` | Unit coverage for registry + each tool |
| `tests/security/test_agent_workspace_isolation.py` | Foreign `document_id` isolation for new tools |
| `tests/unit/test_agent_*.py` | Updated registry/service constructor call sites |

## Behavior Added

- Planner receives JSON schemas for all five whitelist tools.
- Document tools load chunks via `DocumentRepository` + `IngestionRepository` scoped by `workspace_id`.
- Foreign / missing document IDs return `document_not_available` with empty citations (no title/content leak).
- Non-indexed / empty documents return `document_not_indexed` / `document_empty`.
- Summarize caps input (~6k tokens/batch, up to 3 batches) and merges partial summaries when needed.
- Suggest-debugging calls `search_knowledge_base` internally; insufficient retrieval returns a safe empty checklist.
- Tool LLM calls log `usage_events` with `operation=agent_step` and purposes like `agent_tool:summarize_document`.
- ToolExecutor continues to persist every invocation to `agent_tool_calls` (success and sanitized failures).

## Tests Added

- Unit: registry has five tools; summarize/extract/compare/suggest happy paths; foreign/empty/not-indexed failures; compare arity validation; suggest grounding + insufficient context
- Security (Docker): foreign `document_id` for summarize, extract, compare — no foreign title/content leak; LLM not invoked
- Existing agent unit suites updated for new `build_tool_registry` / `AgentService` signatures

## Decisions Made

1. **Story arity wins for compare:** acceptance criteria say 2–5 documents; architecture table previously said 2–3 — updated docs to 2–5.
2. **Repos over DocumentService for chunk load:** agents depend on `documents` + ingestion repos for indexed chunk text; avoids pulling storage/upload into tool path.
3. **Token budget heuristic:** tool input caps use chars/4 (not tiktoken) so CI/unit tests do not require downloading BPE encodings.
4. **Safe failure codes:** `document_not_available` covers both missing and cross-workspace IDs (indistinguishable to the caller).
5. **Executor passes `agent_run_id`:** required so tool LLM steps attach to the same usage metadata as planning/summary.
6. **DOCUMENT_DATA delimiters:** tool prompts wrap chunk text to reduce prompt-injection risk (ADR-006 observation wrapping for the loop remains deferred).

## Known Limitations

- Summarize/compare truncate very large docs to the token budget (noted in summarize output).
- `suggest_debugging_steps` does not accept explicit `document_id` filters (search-only grounding).
- AGENT-009 list API and AUDIT-006 agent-run audit events are out of scope.
- ADR-006 delimiter wrapping for tool observations in the orchestrator message history remains deferred.

## Follow-up Items

- AGENT-009: `GET .../tool-calls` list API
- AUDIT-006: Agent run audit events
- Optional: expose richer per-tool usage purpose aggregation in admin usage summaries

## Verification

```bash
pytest tests/unit/test_agent_tools_batch_002.py -q
pytest tests/unit/test_agent_orchestrator.py tests/unit/test_agent_service.py tests/unit/test_agent_tool_executor.py -q
# Docker (security isolation for document tools):
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm test \
  pytest tests/security/test_agent_workspace_isolation.py -q
```

## Review fix cycle

**Finding:** `_normalize_steps` trusted LLM `grounded=true` when `source_document_id` was null or not in citation set, so generic/unsourced steps could be presented as internal facts.

**Fix:**
- `grounded=True` only when `source_document_id ∈ allowed_document_ids`
- Otherwise force `grounded=False`, `speculative=True`, and clear invalid source
- Prompt aligned with DOCUMENT_DATA / untrusted-data framing used by document tools
- Unit test: `test_normalize_steps_rejects_unsourced_grounded_claims`
