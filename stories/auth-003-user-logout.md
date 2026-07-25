# AUTH-003 — User Logout

> **Epic:** Epic 1: Authentication and User Accounts  
> **Story ID:** AUTH-003  
> **Status:** in_progress  
> **Implementation note (draft):** [AUTH-003](../docs/implementation-notes/AUTH-003.md)

**User Story**

> As an authenticated user, I want to log out, so that my session token is invalidated on shared devices.

**Product Rationale**

Basic session hygiene for portfolio credibility; even with stateless JWT, logout documents intent.

**Functional Requirements**

- `POST /auth/logout` requires valid JWT
- Client-side token discard is primary mechanism
- Optional: token blocklist in Redis for MVP if feasible; otherwise document client-side logout

**Acceptance Criteria**

- Given I am authenticated  
  When I call logout  
  Then the API returns 204 and subsequent requests with the same token are rejected if blocklist is implemented

- Given blocklist is not implemented  
  When I log out  
  Then the API confirms logout and documentation states client must discard token

**Priority:** P1  
**Dependencies:** AUTH-002  
**Notes for Engineering:** Stateless JWT logout is acceptable for MVP if documented; blocklist is P1 polish.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
