# WS-005 — Role-Based Permission Matrix

> **Epic:** Epic 2: Workspace Management and RBAC  
> **Story ID:** WS-005
> **Status:** completed

**User Story**

> As the system, I want to enforce role permissions on every protected action, so that Viewers cannot mutate documents.

**Product Rationale**

Permission enforcement is mandatory for multi-tenant trust and portfolio security narrative.

**Functional Requirements**

Permission matrix (minimum):

| Action | Owner | Admin | Member | Viewer |
|--------|-------|-------|--------|--------|
| Upload/delete/reindex docs | ✓ | ✓ | ✓ | ✗ |
| Ask questions / agent runs | ✓ | ✓ | ✓ | ✓ |
| Manage members | ✓ | ✓ | ✗ | ✗ |
| View admin dashboard | ✓ | ✓ | ✗ | ✗ |
| Delete workspace | ✓ | ✗ | ✗ | ✗ |

- Permission checks in service layer, not only routes
- Violations return 403 and log audit event

**Acceptance Criteria**

- Given I am a Viewer  
  When I upload a document  
  Then the API returns 403

- Given I am a Member  
  When I ask a question  
  Then the request succeeds

**Priority:** P0  
**Dependencies:** WS-003  
**Notes for Engineering:** Centralize in `PermissionService` or decorator; unit test matrix.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
