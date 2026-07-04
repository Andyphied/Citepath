# WS-003 — Invite and Manage Members

> **Epic:** Epic 2: Workspace Management and RBAC  
> **Story ID:** WS-003
> **Status:** completed

**User Story**

> As a Workspace Owner, I want to add members to my workspace, so that my team can collaborate.

**Product Rationale**

Collaboration requires membership management; Owner/Admin must control access.

**Functional Requirements**

- `POST /workspaces/{workspace_id}/members` accepts `email`, `role`
- Only Owner and Admin can add members
- Valid roles: `owner`, `admin`, `member`, `viewer`
- User must exist (registered) or return 404 for unknown email
- Cannot demote/remove last Owner

**Acceptance Criteria**

- Given I am Workspace Owner  
  When I invite `engineer@example.com` as Member  
  Then they appear in workspace members

- Given I am a Viewer  
  When I try to add a member  
  Then the API returns 403

**Priority:** P0  
**Dependencies:** WS-001, AUTH-001  
**Notes for Engineering:** `PATCH`/`DELETE` for role change and removal in same story scope or WS-004.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
