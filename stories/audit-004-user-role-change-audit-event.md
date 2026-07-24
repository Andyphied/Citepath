# AUDIT-004 — User Role Change Audit Event

> **Epic:** Epic 10: Audit Logs and Security Events  
> **Story ID:** AUDIT-004
> **Status:** in_progress

**User Story**

> As a Workspace Owner, I want role changes audited, so that permission changes are accountable.

**Functional Requirements**

- Event: `member.role_changed` with old_role, new_role, target_user_id

**Acceptance Criteria**

- Given Owner changes Member to Viewer  
  When change succeeds  
  Then audit log captures old and new roles

**Priority:** P1  
**Dependencies:** WS-004  
**Notes for Engineering:** Include actor user_id.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
