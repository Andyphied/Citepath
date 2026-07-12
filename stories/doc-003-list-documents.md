# DOC-003 — List Documents

> **Epic:** Epic 3: Document Upload and Management  
> **Story ID:** DOC-003
> **Status:** completed
> **Completed:** 2026-07-12
> **Implementation note:** [DOC-003](../docs/implementation-notes/DOC-003.md)

**User Story**

> As a workspace member, I want to list documents in my workspace, so that I can see what knowledge is indexed.

**Product Rationale**

Users need visibility into indexed corpus; admin dashboard depends on this.

**Functional Requirements**

- `GET /workspaces/{workspace_id}/documents` with pagination
- Returns `id`, `title`, `file_type`, `status`, `uploaded_by`, `created_at`, `updated_at`
- Filter by status optional
- All roles including Viewer can list

**Acceptance Criteria**

- Given 5 documents in my workspace  
  When I list documents  
  Then I see all 5 with current status

- Given pagination limit=2  
  When I request page 2  
  Then I receive the next 2 documents

**Priority:** P0  
**Dependencies:** DOC-001  
**Notes for Engineering:** Index on `(workspace_id, created_at)`.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
