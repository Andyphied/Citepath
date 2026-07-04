# ADR-005: Workspace Isolation Model

## Status

Accepted

## Context

AtlasOps AI is multi-tenant. Cross-workspace data leakage would destroy trust and fail MVP success criteria. Isolation must apply to documents, chunks, vector search, conversations, agent runs, usage, and audit data.

## Decision

Enforce workspace isolation at **three layers**:

1. **Application authorization** — JWT + `workspace_members` check + role permission before any workspace route
2. **Service layer** — All operations receive `WorkspaceContext`; services reject missing workspace
3. **Repository/query layer** — Every tenant-owned SQL query includes `WHERE workspace_id = :workspace_id`

Additionally:
- Denormalize `workspace_id` on child tables (`messages`, `document_chunks`, `agent_tool_calls`) for defense in depth
- Storage keys prefixed with `{workspace_id}/`
- Celery tasks validate resource workspace at execution time

Return **404** (not 403) when a **tenant-owned resource** ID exists in another workspace to prevent enumeration of documents, chunks, conversations, and similar nested entities.

For **workspace membership** endpoints (`GET /workspaces/{workspace_id}`, future workspace-scoped routes), return **403 forbidden** when the authenticated user is not a member (including unknown workspace IDs mapped to the same denial envelope). This avoids workspace existence enumeration while clearly signaling an authorization failure at the workspace boundary.

## Consequences

**Positive:**
- Defense in depth; bug in one layer may be caught by another
- Clear code review rule: no repository method without `workspace_id`
- Testable with explicit security test suite

**Negative:**
- Denormalized `workspace_id` requires consistency on insert
- Slightly verbose query signatures
- 404 vs 403 semantics must be documented for API consumers

## Alternatives Considered

| Alternative | Why not selected |
|-------------|------------------|
| **DB row-level security (RLS) only** | Powerful but harder local dev/debug; team must still pass context; use as future enhancement |
| **Separate database per workspace** | Absurd ops cost for MVP |
| **Application-only filtering** | Single missed query causes leakage; insufficient for portfolio security story |
| **API gateway tenancy** | Does not protect worker tasks or direct DB access |

## Implementation Notes

- `WorkspaceContext` dataclass injected via FastAPI dependencies
- Base repository: `class WorkspaceScopedRepository: def _filter(self, q, workspace_id)`
- Vector search SQL must never omit workspace predicate
- **Required tests:** `tests/security/test_workspace_isolation.py` with two workspaces
- Code review checklist item: "Does this query filter workspace_id?"
- Audit `failed_authorization` on 403 attempts
