# AUTH-006 — Auth Error Responses

> **Epic:** Epic 1: Authentication and User Accounts  
> **Story ID:** AUTH-006
> **Status:** in_progress

**User Story**

> As a developer integrating the API, I want consistent auth error responses, so that I can handle failures predictably.

**Product Rationale**

Structured errors reduce integration friction and demonstrate API maturity.

**Functional Requirements**

- Auth errors use consistent JSON shape: `{ "error": { "code", "message", "details" } }`
- Codes include: `invalid_credentials`, `token_expired`, `token_invalid`, `unauthorized`
- HTTP status codes match semantics (401, 403, 409, 422)

**Acceptance Criteria**

- Given any auth failure  
  When the API responds  
  Then the body includes `error.code` and `error.message`

**Priority:** P1  
**Dependencies:** AUTH-005  
**Notes for Engineering:** Shared error schema is owned by OBS-004 (`error_response()`). Story note historically referenced OBS-005; that is outdated.

---

---

### Epic 2: Workspace Management and RBAC


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
