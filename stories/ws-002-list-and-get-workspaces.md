# WS-002 — List and Get Workspaces

> **Epic:** Epic 2: Workspace Management and RBAC  
> **Story ID:** WS-002
> **Status:** in_progress

**User Story**

> As a user, I want to list workspaces I belong to, so that I can switch between teams.

**Product Rationale**

Multi-workspace membership is core to the data model; users need discovery and selection.

**Functional Requirements**

- `GET /workspaces` returns workspaces where user is a member, including role
- `GET /workspaces/{workspace_id}` returns workspace details if member
- Non-members receive 403

**Acceptance Criteria**

- Given I belong to Workspace A and B  
  When I list workspaces  
  Then both appear with my role

- Given I am not a member of Workspace C  
  When I request Workspace C  
  Then the API returns 403

**Priority:** P0  
**Dependencies:** WS-001  
**Notes for Engineering:** Include member count optionally; paginate if list grows.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
