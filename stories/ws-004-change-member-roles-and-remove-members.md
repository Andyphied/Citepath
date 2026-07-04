# WS-004 — Change Member Roles and Remove Members

> **Epic:** Epic 2: Workspace Management and RBAC  
> **Story ID:** WS-004
> **Status:** completed

**User Story**

> As a Workspace Owner, I want to change member roles or remove members, so that I can enforce least privilege.

**Product Rationale**

RBAC is incomplete without role updates and removal; required for security demos.

**Functional Requirements**

- `PATCH /workspaces/{workspace_id}/members/{user_id}` updates role
- `DELETE /workspaces/{workspace_id}/members/{user_id}` removes member
- Only Owner can assign Owner role; Admin cannot modify Owner
- Removing self allowed unless last Owner

**Acceptance Criteria**

- Given I am Owner  
  When I change a Member to Viewer  
  Then their permissions update immediately

- Given only one Owner remains  
  When Owner tries to remove themselves  
  Then the API returns 400 with clear message

**Priority:** P0  
**Dependencies:** WS-003  
**Notes for Engineering:** Emit audit event (AUDIT-005).


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
