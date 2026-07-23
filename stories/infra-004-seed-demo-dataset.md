# INFRA-004 — Seed Demo Dataset

> **Epic:** Epic 12: Deployment and Developer Experience  
> **Story ID:** INFRA-004
> **Status:** completed
> **Completed:** 2026-07-23
> **Implementation note:** [INFRA-004](../docs/implementation-notes/INFRA-004.md)

**User Story**

> As a demo presenter, I want a seed script for Northstar Cloud documents, so that I can show realistic answers quickly.

**Product Rationale**

Demo dataset unlocks portfolio scenarios without manual upload.

**Functional Requirements**

- Script creates demo workspace, user, and uploads sample docs from PRD:
  - billing-api-runbook.md, auth-service-architecture.md, deployment-process.md, incident-2025-08-billing-502.md, etc.
- Triggers ingestion; idempotent re-run safe

**Acceptance Criteria**

- Given seed script runs  
  When ingestion completes  
  Then billing 502 demo question returns cited answer

**Priority:** P1  
**Dependencies:** DOC-001, ING-001, INFRA-003  
**Notes for Engineering:** Check in markdown files under `demo_data/`.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
