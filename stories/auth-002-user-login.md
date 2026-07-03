# AUTH-002 — User Login

> **Epic:** Epic 1: Authentication and User Accounts  
> **Story ID:** AUTH-002
> **Status:** completed
> **Completed:** 2026-07-04
> **Implementation note:** [AUTH-002](../docs/implementation-notes/AUTH-002.md)

**User Story**

> As a registered user, I want to log in with email and password, so that I can access my workspaces and data.

**Product Rationale**

Login enables returning users to resume work and attaches identity to all subsequent API calls.

**Functional Requirements**

- `POST /auth/login` accepts `email`, `password`
- Validates credentials against hashed password
- Returns JWT access token and token expiry
- Invalid credentials return 401 without revealing whether email exists

**Acceptance Criteria**

- Given valid credentials  
  When I log in  
  Then I receive a JWT and can call authenticated endpoints

- Given invalid password  
  When I log in  
  Then the API returns 401 Unauthorized

**Priority:** P0  
**Dependencies:** AUTH-001  
**Notes for Engineering:** Rate-limit login attempts per IP/email to reduce brute-force risk.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
