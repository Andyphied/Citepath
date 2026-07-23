# AUDIT-006 — Agent Run Audit Event

> **Epic:** Epic 10: Audit Logs and Security Events  
> **Story ID:** AUDIT-006
> **Status:** in_progress

**User Story**

> As an Admin, I want agent investigations audited, so that automated AI actions are traceable.

**Functional Requirements**

- Event: `agent.run_completed` with agent_run_id, objective summary, tool call count, status

**Acceptance Criteria**

- Given agent run completes  
  When status is completed  
  Then audit log entry is created

**Priority:** P1  
**Dependencies:** AGENT-008  
**Notes for Engineering:** Truncate objective in audit payload.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
