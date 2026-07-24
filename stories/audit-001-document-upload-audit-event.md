# AUDIT-001 — Document Upload Audit Event

> **Epic:** Epic 10: Audit Logs and Security Events  
> **Story ID:** AUDIT-001
> **Status:** in_progress

**User Story**

> As a Workspace Owner, I want document uploads audited, so that I can trace who added knowledge.

**Product Rationale**

Audit trail for sensitive content changes.

**Functional Requirements**

- Event: `document.uploaded` with actor, workspace_id, document_id, title, timestamp
- Stored in `audit_logs` append-only table

**Acceptance Criteria**

- Given Admin uploads document  
  When upload succeeds  
  Then audit log entry exists with actor and document_id

**Priority:** P1  
**Dependencies:** DOC-001  
**Notes for Engineering:** Never log file content in audit.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
