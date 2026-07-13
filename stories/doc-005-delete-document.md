# DOC-005 — Delete Document

> **Epic:** Epic 3: Document Upload and Management  
> **Story ID:** DOC-005
> **Status:** completed
> **Completed:** 2026-07-13
> **Implementation note:** [DOC-005](../docs/implementation-notes/DOC-005.md)

**User Story**

> As an Admin, I want to delete a document, so that outdated or incorrect knowledge is removed.

**Product Rationale**

Corpus hygiene; deletion must cascade chunks and embeddings.

**Functional Requirements**

- `DELETE /workspaces/{workspace_id}/documents/{document_id}`
- Requires Admin, Member, or Owner (not Viewer)
- Deletes file from storage, chunks, embeddings, and document record
- Emits audit event (AUDIT-002)
- Returns 204

**Acceptance Criteria**

- Given an indexed document  
  When I delete it  
  Then document and all chunks are removed and no longer appear in search

- Given a Viewer  
  When they attempt delete  
  Then the API returns 403

**Priority:** P0  
**Dependencies:** DOC-001, ING-006, WS-005  
**Notes for Engineering:** Use transaction or compensating delete; soft-delete optional P2.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
