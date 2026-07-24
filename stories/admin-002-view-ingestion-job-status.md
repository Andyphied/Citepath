# ADMIN-002 — View Ingestion Job Status

> **Epic:** Epic 9: Admin Dashboard  
> **Story ID:** ADMIN-002
> **Status:** in_progress

**User Story**

> As an Admin, I want to see ingestion jobs and failures, so that I can fix indexing issues quickly.

**Product Rationale**

Failed jobs block the core loop; admins must see them.

**Functional Requirements**

- `GET /workspaces/{workspace_id}/admin/ingestion-jobs`
- Filter by status; show failed jobs prominently with error_message
- Pagination supported

**Acceptance Criteria**

- Given a failed ingestion job  
  When Admin views ingestion jobs  
  Then failed job appears with error reason

**Priority:** P1  
**Dependencies:** ING-006  
**Notes for Engineering:** Include document title in join.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
