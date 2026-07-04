# OBS-001 — Health Check Endpoint

> **Epic:** Epic 11: Observability and Reliability  
> **Story ID:** OBS-001
> **Status:** completed
> **Completed:** 2026-07-04
> **Implementation note:** [OBS-001](../docs/implementation-notes/OBS-001.md)

**User Story**

> As an operator, I want a health check endpoint, so that I can verify the API and dependencies are up.

**Product Rationale**

Required for Docker, CI, and cloud load balancers.

**Functional Requirements**

- `GET /health` returns 200 when API alive
- Optional `GET /health/ready` checks DB, Redis, worker connectivity
- Returns component status JSON

**Acceptance Criteria**

- Given all dependencies healthy  
  When readiness check runs  
  Then response is 200 with `{ "status": "ok", "database": "ok", "redis": "ok" }`

- Given database unreachable  
  When readiness check runs  
  Then response is 503

**Priority:** P0  
**Dependencies:** INFRA-001  
**Notes for Engineering:** Liveness vs readiness separation for K8s/ECS.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
