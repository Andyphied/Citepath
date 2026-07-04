# AUTH-004 — Current User Endpoint

> **Epic:** Epic 1: Authentication and User Accounts  
> **Story ID:** AUTH-004
> **Status:** in_progress

**User Story**

> As an authenticated user, I want to retrieve my profile, so that the UI can display my identity and permissions context.

**Product Rationale**

Required for frontend session bootstrap and debugging auth issues.

**Functional Requirements**

- `GET /auth/me` returns `id`, `email`, `name`, `created_at`
- Requires valid JWT in `Authorization: Bearer` header
- Does not return password hash or internal fields

**Acceptance Criteria**

- Given a valid JWT  
  When I call `/auth/me`  
  Then I receive my user profile

- Given an expired or missing token  
  When I call `/auth/me`  
  Then the API returns 401

**Priority:** P0  
**Dependencies:** AUTH-002  
**Notes for Engineering:** Attach user to request context via dependency injection middleware.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
