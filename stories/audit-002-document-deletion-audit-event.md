# AUDIT-002 — Document Deletion Audit Event

> **Epic:** Epic 10: Audit Logs and Security Events  
> **Story ID:** AUDIT-002
> **Status:** in_progress  
> **Note:** Emitter verified in AUDIT-BATCH-001; mark completed at Gate 6.

**User Story**

> As a Workspace Owner, I want deletions audited, so that removals are traceable.

**Functional Requirements**

- Event: `document.deleted` with actor, document_id, title

**Acceptance Criteria**

- Given document deleted  
  When deletion completes  
  Then audit log records the event

**Priority:** P1  
**Dependencies:** DOC-005  
**Notes for Engineering:** Include soft metadata snapshot (title only).


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
