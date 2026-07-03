# AUTH-001 — User Registration

> **Epic:** Epic 1: Authentication and User Accounts  
> **Story ID:** AUTH-001
> **Status:** completed
> **Completed:** 2026-07-04
> **Implementation note:** [AUTH-001](../docs/implementation-notes/AUTH-001.md)

**User Story**

> As a new user, I want to register with email and password, so that I can access AtlasOps AI.

**Product Rationale**

Registration is the entry point to the product loop. Without accounts, workspace isolation and RBAC cannot exist.

**Functional Requirements**

- `POST /auth/register` accepts `email`, `password`, optional `name`
- Email must be unique and valid format
- Password minimum length enforced (e.g., 8 characters)
- Password stored as bcrypt/argon2 hash; never plaintext
- Returns user object (no password) and JWT on success
- Duplicate email returns 409 Conflict

**Acceptance Criteria**

- Given a valid email and password  
  When I submit registration  
  Then a user record is created and I receive a JWT access token

- Given an email already registered  
  When I submit registration  
  Then the API returns 409 with a clear error message

- Given a password below minimum length  
  When I submit registration  
  Then the API returns 422 with validation details

**Priority:** P0  
**Dependencies:** None  
**Notes for Engineering:** Use Pydantic validation; consider email normalization (lowercase). JWT expiry configurable via env.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
