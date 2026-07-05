# OBS-004 — Standard API Error Format

> **Epic:** Epic 11: Observability and Reliability  
> **Story ID:** OBS-004
> **Status:** in_progress

**User Story**

> As an API consumer, I want consistent error responses, so that I can handle failures uniformly.

**Product Rationale**

Pairs with AUTH-006 for full API consistency.

**Functional Requirements**

- Shape: `{ "error": { "code", "message", "details", "request_id" } }`
- Map unhandled exceptions to 500 with generic message; log stack trace server-side

**Acceptance Criteria**

- Given validation error  
  When request fails  
  Then 422 returns structured error with field details

**Priority:** P1  
**Dependencies:** OBS-003  
**Notes for Engineering:** Register FastAPI exception handlers globally.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
