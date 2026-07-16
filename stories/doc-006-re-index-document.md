# DOC-006 — Re-index Document

> **Epic:** Epic 3: Document Upload and Management  
> **Story ID:** DOC-006
> **Status:** completed
> **Completed:** 2026-07-16
> **Implementation note:** [DOC-006](../docs/implementation-notes/DOC-006.md)

**User Story**

> As an Admin, I want to re-index a document, so that updated extraction or embedding models are applied.

**Product Rationale**

Re-index proves pipeline idempotency and supports demo recovery after failures.

**Functional Requirements**

- `POST /workspaces/{workspace_id}/documents/{document_id}/reindex`
- Deletes existing chunks for document, resets status to `processing`, enqueues new ingestion job
- Emits audit event (AUDIT-003)
- Requires upload permissions (not Viewer)

**Acceptance Criteria**

- Given an indexed document  
  When I trigger re-index  
  Then old chunks are replaced and status transitions to `indexed` on success

**Priority:** P1  
**Dependencies:** DOC-001, ING-001  
**Notes for Engineering:** Prevent concurrent re-index jobs for same document.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
