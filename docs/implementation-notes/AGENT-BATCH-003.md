# AGENT-BATCH-003 Implementation Note

## Summary

Delivered tool-call listing for agent runs (AGENT-009) and `agent.run_completed` audit emission on successful and failed run completion (AUDIT-006). Persistence of tool calls already existed via `ToolExecutor`; this batch exposes the read API and wires audit through existing `AuditRepository`.

## Stories Covered

| Story | Delivered |
|-------|-----------|
| AGENT-009 | `GET /workspaces/{id}/agent-runs/{id}/tool-calls` with ordered, truncated I/O + latency |
| AUDIT-006 | `agent.run_completed` audit on completed and failed runs |

## Files Changed

| File | Purpose |
|------|---------|
| `app/modules/agents/schemas.py` | `AgentToolCallResponse`, `AgentToolCallListResponse` |
| `app/modules/agents/service.py` | `list_tool_calls`; audit emit; shared `_can_view_run` |
| `app/modules/agents/repository.py` | Direct `AgentToolCall.workspace_id` filter (no cartesian join) |
| `app/api/routes/agent_runs.py` | Tool-calls GET route |
| `app/api/deps.py` | Inject `AuditRepository` into `AgentService` |
| `tests/unit/test_agent_service.py` | List + audit unit coverage |
| `tests/api/test_agent_runs.py` | API/RBAC/isolation/audit assertions |
| `docs/08-agent-architecture.md` | Tool-calls API + event name |
| `docs/09-security-and-rbac.md` | Event type `agent.run_completed` |
| `stories/agent-009-*.md`, `stories/audit-006-*.md` | Status `in_progress` |

## Behavior Added

- `GET .../agent-runs/{id}/tool-calls` requires `RUN_AGENT` (includes Viewer).
- Visibility: run creator always; Owner/Admin may inspect any run in the workspace; other members get `404`.
- Cross-workspace / missing run → `404`; non-member → `403`; unauthenticated → `401`.
- Response `{ "items": [{ id, tool_name, input, output, status, latency_ms, created_at }] }` ordered by `created_at`, then `id`.
- On run terminal state (completed or failed), emits audit `agent.run_completed` with `agent_run_id`, truncated `objective` (200 chars + ellipsis), `tool_call_count`, `status`.
- Audit flush precedes `update_run` commit (same pattern as document delete/reindex).

## Tests Added

**Unit:**

- Ordered tool-call list mapping
- Member denied other user's run; Admin allowed
- Audit on success and orchestration failure
- Objective truncation in audit metadata

**API (Docker):**

- Happy path lists tool calls + audit row after completed run
- Failed unknown-tool run still writes `agent.run_completed` with `status=failed`
- Cross-workspace tool-calls → 404
- Member cannot list Owner's run → 404; Owner can
- Admin can list Member's run
- Long objective truncated in audit payload

## Decisions Made

1. **Event type `agent.run_completed`** (dotted) — matches AUDIT-006 story and existing document audit style (`document.deleted`); architecture docs previously used `agent_run_completed` and were updated.
2. **Admin/Owner cross-user visibility** for tool-calls and GET run — aligns with `docs/06-api-design.md`; Member/Viewer remain creator-only.
3. **Emit audit on failed runs** — story AC mentions completed; Gate 1 scope required failed completion too; `status` in metadata distinguishes outcomes.
4. **No rebuild of tool-call logging** — `ToolExecutor` truncation/latency persistence unchanged.

## Known Limitations

- Full object-storage for non-truncated tool outputs remains P2 (story note).
- `agent_run_started` audit not emitted (not in this batch).
- API/security Docker tests require local Docker + pgvector container.

## Follow-up Items

- **AUDIT-007:** Query audit logs API (Admin)
- **ADMIN-***: Dashboard widgets consuming tool-call / audit data
- Optional: commit story status markers for AGENT-004–007 if still pending in git
