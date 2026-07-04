# WS-006 — Active Workspace Context

> **Epic:** Epic 2: Workspace Management and RBAC  
> **Story ID:** WS-006
> **Status:** completed

**User Story**

> As a user, I want all API calls scoped to a workspace, so that my queries only access that workspace's data.

**Product Rationale**

Explicit workspace scoping prevents accidental cross-tenant access in URL design.

**Functional Requirements**

- All resource routes under `/workspaces/{workspace_id}/...`
- Middleware verifies user membership before handler execution
- `workspace_id` injected into service/repository layer for all queries

**Acceptance Criteria**

- Given I belong to Workspace A  
  When I ask a question in Workspace A  
  Then retrieval only searches Workspace A documents

- Given I do not belong to Workspace B  
  When I request any Workspace B resource  
  Then the API returns 403

**Priority:** P0  
**Dependencies:** WS-002, WS-005  
**Notes for Engineering:** Every DB query must include `workspace_id` filter; add integration tests for isolation.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
