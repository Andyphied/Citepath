# AGENT-009 — Log Agent Tool Calls

> **Epic:** Epic 7: AI Agent Incident Investigation  
> **Story ID:** AGENT-009
> **Status:** in_progress

**User Story**

> As an Admin, I want agent tool calls logged, so that I can audit agent behavior and debug failures.

**Product Rationale**

Tool call visibility demonstrates controlled agent execution.

**Functional Requirements**

- `agent_tool_calls`: tool_name, input, output (truncated), latency_ms, created_at
- `GET /workspaces/{workspace_id}/agent-runs/{id}/tool-calls`
- Emit audit event on agent run completion (AUDIT-006)

**Acceptance Criteria**

- Given agent run with 3 tool calls  
  When Admin fetches tool calls  
  Then all 3 are listed in order with inputs and outputs

**Priority:** P1  
**Dependencies:** AGENT-002  
**Notes for Engineering:** Truncate large outputs in DB; store full in object storage P2.

---

---

### Epic 8: Usage Tracking and Cost Visibility


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
