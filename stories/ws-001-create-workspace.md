# WS-001 — Create Workspace

> **Epic:** Epic 2: Workspace Management and RBAC  
> **Story ID:** WS-001
> **Status:** completed
> **Completed:** 2026-07-04
> **Implementation note:** [WS-001](../docs/implementation-notes/WS-001.md)

**User Story**

> As a new user, I want to create a workspace, so that my team has an isolated knowledge container.

**Product Rationale**

Workspaces are the tenancy boundary for all documents, chunks, conversations, and usage.

**Functional Requirements**

- `POST /workspaces` accepts `name`, optional `slug`
- Creator is assigned `Owner` role automatically
- Slug auto-generated from name if omitted; must be unique
- Returns workspace with `id`, `name`, `slug`, `created_at`

**Acceptance Criteria**

- Given I am authenticated  
  When I create a workspace named "Northstar Cloud"  
  Then a workspace is created and I am its Owner

- Given a duplicate slug  
  When I create a workspace  
  Then the API returns 409

**Priority:** P0  
**Dependencies:** AUTH-005  
**Notes for Engineering:** Slug used in URLs; validate slug format (lowercase, hyphens).


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
