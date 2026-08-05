# INFRA-008 — OpenAPI API Documentation

> **Epic:** Epic 12: Deployment and Developer Experience  
> **Story ID:** INFRA-008
> **Status:** in_progress

**User Story**

> As an integrator, I want auto-generated API docs, so that I can explore endpoints without reading source code.

**Product Rationale**

FastAPI OpenAPI is zero-cost documentation; supports API-first MVP.

**Functional Requirements**

- Swagger UI at `/docs`, ReDoc at `/redoc`
- All endpoints documented with request/response schemas
- Auth scheme documented (Bearer JWT)

**Acceptance Criteria**

- Given running API  
  When I open `/docs`  
  Then all MVP endpoints are listed with schemas

**Priority:** P1  
**Dependencies:** All API stories  
**Notes for Engineering:** Add examples on key endpoints (query, agent-run).

---


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
