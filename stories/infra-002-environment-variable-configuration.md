# INFRA-002 — Environment Variable Configuration

> **Epic:** Epic 12: Deployment and Developer Experience  
> **Story ID:** INFRA-002
> **Status:** completed
> **Completed:** 2026-07-03
> **Implementation note:** [INFRA-002](../docs/implementation-notes/INFRA-002.md)

**User Story**

> As a developer, I want configuration via environment variables, so that secrets are not hardcoded.

**Product Rationale**

12-factor app pattern; required for cloud deployment.

**Functional Requirements**

- Config: DATABASE_URL, REDIS_URL, JWT_SECRET, LLM_API_KEY, EMBEDDING_MODEL, STORAGE_PATH, etc.
- Validate required vars on startup; fail fast with clear message
- `.env.example` documents all vars

**Acceptance Criteria**

- Given missing JWT_SECRET  
  When API starts  
  Then startup fails with descriptive error

**Priority:** P0  
**Dependencies:** None  
**Notes for Engineering:** Pydantic Settings; never commit `.env`.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
