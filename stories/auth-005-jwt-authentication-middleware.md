# AUTH-005 — JWT Authentication Middleware

> **Epic:** Epic 1: Authentication and User Accounts  
> **Story ID:** AUTH-005
> **Status:** completed
> **Completed:** 2026-07-04
> **Implementation note:** [AUTH-005](../docs/implementation-notes/AUTH-005.md)

**User Story**

> As the system, I want to validate JWTs on protected routes, so that only authenticated users access workspace data.

**Product Rationale**

Central auth middleware is the foundation for RBAC and workspace isolation.

**Functional Requirements**

- Middleware extracts Bearer token, validates signature and expiry
- Injects `current_user` into request context
- Unauthenticated requests to protected routes return 401
- Malformed tokens return 401 with structured error

**Acceptance Criteria**

- Given no Authorization header  
  When I call a protected endpoint  
  Then the API returns 401

- Given an expired JWT  
  When I call a protected endpoint  
  Then the API returns 401 with `token_expired` error code

**Priority:** P0  
**Dependencies:** AUTH-002  
**Notes for Engineering:** Use FastAPI `Depends`; secret key from env; algorithm HS256 or RS256.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
