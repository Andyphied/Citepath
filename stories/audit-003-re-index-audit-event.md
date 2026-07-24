# AUDIT-003 — Re-index Audit Event

> **Epic:** Epic 10: Audit Logs and Security Events  
> **Story ID:** AUDIT-003
> **Status:** in_progress  
> **Note:** Emitter verified in AUDIT-BATCH-001; mark completed at Gate 6.

**User Story**

> As a Workspace Owner, I want re-index actions audited, so that corpus changes are traceable.

**Functional Requirements**

- Event: `document.reindex_requested`

**Acceptance Criteria**

- Given re-index triggered  
  When job enqueued  
  Then audit log entry is created

**Priority:** P1  
**Dependencies:** DOC-006  
**Notes for Engineering:** None.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
