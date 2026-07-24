# ADMIN-003 — View Recent Questions

> **Epic:** Epic 9: Admin Dashboard  
> **Story ID:** ADMIN-003
> **Status:** in_progress

**User Story**

> As an Admin, I want to see recent questions asked in the workspace, so that I understand how the team uses AtlasOps.

**Product Rationale**

Lightweight usage insight without advanced analytics.

**Functional Requirements**

- List recent conversations/messages with user, timestamp, question preview
- No need to expose full LLM prompts
- Paginated, last 50 default

**Acceptance Criteria**

- Given engineers asked 3 questions today  
  When Admin views recent questions  
  Then all 3 appear with timestamps

**Priority:** P2  
**Dependencies:** RAG-006  
**Notes for Engineering:** Privacy: workspace members only via admin role.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
