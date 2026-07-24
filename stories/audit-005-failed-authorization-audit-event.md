# AUDIT-005 — Failed Authorization Audit Event

> **Epic:** Epic 10: Audit Logs and Security Events  
> **Story ID:** AUDIT-005
> **Status:** in_progress  
> **Note:** Emitter verified + hardened in AUDIT-BATCH-001; mark completed at Gate 6.

**User Story**

> As a security-conscious admin, I want failed authorization attempts logged, so that I can detect abuse.

**Functional Requirements**

- Event: `authz.denied` with actor, resource, action, workspace_id
- Do not log at debug only — persist to audit_logs

**Acceptance Criteria**

- Given Viewer attempts document delete  
  When request is denied  
  Then audit log records authz.denied

**Priority:** P1  
**Dependencies:** WS-005  
**Notes for Engineering:** Rate-limit audit writes for repeated spam.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
