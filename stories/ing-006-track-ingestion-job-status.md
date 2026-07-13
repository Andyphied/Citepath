# ING-006 — Track Ingestion Job Status

> **Epic:** Epic 4: Ingestion Pipeline  
> **Story ID:** ING-006
> **Status:** completed
> **Completed:** 2026-07-13
> **Implementation note:** [ING-006](../docs/implementation-notes/ING-006.md)

**User Story**

> As an Admin, I want to see ingestion job status, so that I know when documents are ready for questions.

**Product Rationale**

Job visibility is essential for async UX and admin dashboard.

**Functional Requirements**

- Job statuses: `pending`, `processing`, `completed`, `failed`
- Fields: `document_id`, `workspace_id`, `started_at`, `completed_at`, `error_message`, `retry_count`
- `GET` via admin endpoint or document detail
- On success: document status → `indexed`; job → `completed`

**Acceptance Criteria**

- Given ingestion in progress  
  When Admin views job status  
  Then status is `processing`

- Given ingestion completes  
  When Admin views job status  
  Then status is `completed` and document is `indexed`

**Priority:** P0  
**Dependencies:** ING-001  
**Notes for Engineering:** Expose via ADMIN-002.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
