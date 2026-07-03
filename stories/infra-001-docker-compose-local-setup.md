# INFRA-001 — Docker Compose Local Setup

> **Epic:** Epic 12: Deployment and Developer Experience  
> **Story ID:** INFRA-001
> **Status:** completed
> **Completed:** 2026-07-03
> **Implementation note:** [INFRA-001](../docs/implementation-notes/INFRA-001.md)

**User Story**

> As a developer, I want to run the full stack locally with Docker Compose, so that I can develop and demo without manual setup.

**Product Rationale**

Local reproducibility is portfolio table stakes.

**Functional Requirements**

- Services: API, worker, PostgreSQL (pgvector), Redis
- Volume mounts for dev; env file template `.env.example`
- `docker compose up` brings stack to healthy state

**Acceptance Criteria**

- Given fresh clone  
  When I run docker compose up  
  Then health check returns 200 within 2 minutes

**Priority:** P0  
**Dependencies:** OBS-001  
**Notes for Engineering:** Init script enables pgvector extension.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
