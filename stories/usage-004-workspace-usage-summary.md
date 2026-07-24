# USAGE-004 — Workspace Usage Summary

> **Epic:** Epic 8: Usage Tracking and Cost Visibility  
> **Story ID:** USAGE-004
> **Status:** in_progress

**User Story**

> As a Workspace Owner, I want a usage summary for my workspace, so that I can monitor daily AI consumption.

**Product Rationale**

Admin dashboard and portfolio demo need aggregate visibility.

**Functional Requirements**

- `GET /workspaces/{workspace_id}/admin/usage`
- Returns totals: prompt_tokens, completion_tokens, embedding_tokens, estimated_cost, call count
- Optional date range filter (default last 7 days)
- Breakdown by operation type optional P1

**Acceptance Criteria**

- Given 10 queries today  
  When Owner views usage summary  
  Then totals reflect sum of today's usage_events

**Priority:** P1  
**Dependencies:** USAGE-001, USAGE-002, WS-005  
**Notes for Engineering:** Index on (workspace_id, created_at).

---

---

### Epic 9: Admin Dashboard


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
