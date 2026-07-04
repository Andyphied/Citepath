# OBS-003 — Request ID Propagation

> **Epic:** Epic 11: Observability and Reliability  
> **Story ID:** OBS-003
> **Status:** in_progress

**User Story**

> As a developer debugging issues, I want a request ID on every API response, so that I can correlate logs.

**Product Rationale**

Request tracing is low-effort, high-value observability.

**Functional Requirements**

- Generate UUID per request; accept `X-Request-ID` from client if provided
- Return in response header `X-Request-ID`
- Include in all logs and error responses for request

**Acceptance Criteria**

- Given any API call  
  When response returns  
  Then `X-Request-ID` header is present

**Priority:** P1  
**Dependencies:** None  
**Notes for Engineering:** Middleware first in chain.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
