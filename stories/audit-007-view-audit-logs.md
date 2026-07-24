# AUDIT-007 — View Audit Logs

> **Epic:** Epic 10: Audit Logs and Security Events  
> **Story ID:** AUDIT-007
> **Status:** in_progress

**User Story**

> As an Admin, I want to query audit logs, so that I can review workspace activity.

**Functional Requirements**

- `GET /workspaces/{workspace_id}/admin/audit-logs`
- Filter by event type, date range, actor
- Pagination; Owner and Admin only

**Acceptance Criteria**

- Given multiple audit events  
  When Admin queries logs  
  Then events return in reverse chronological order

**Priority:** P1  
**Dependencies:** AUDIT-001 through AUDIT-006  
**Notes for Engineering:** Immutable logs; no delete API.

---

---

### Epic 11: Observability and Reliability


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
