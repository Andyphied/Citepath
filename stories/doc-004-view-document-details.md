# DOC-004 — View Document Details

> **Epic:** Epic 3: Document Upload and Management  
> **Story ID:** DOC-004
> **Status:** completed
> **Completed:** 2026-07-13
> **Implementation note:** [DOC-004](../docs/implementation-notes/DOC-004.md)

**User Story**

> As an engineer, I want to view document details including status and error messages, so that I know if indexing succeeded.

**Product Rationale**

Transparency into ingestion state builds trust during demos and debugging.

**Functional Requirements**

- `GET /workspaces/{workspace_id}/documents/{document_id}`
- Returns metadata, status, chunk count (if indexed), `error_message` if failed, ingestion job reference
- Workspace-scoped; 404 if wrong workspace

**Acceptance Criteria**

- Given a failed document  
  When I view details  
  Then I see status `failed` and `error_message`

- Given an indexed document  
  When I view details  
  Then I see chunk count > 0

**Priority:** P0  
**Dependencies:** DOC-001, ING-007  
**Notes for Engineering:** Do not expose raw storage path to clients.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
