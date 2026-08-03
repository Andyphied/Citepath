# OBS-007 — Background Worker Visibility

> **Epic:** Epic 11: Observability and Reliability  
> **Story ID:** OBS-007
> **Status:** in_progress  
> **Implementation note:** [OBS-BATCH-001](../docs/implementation-notes/OBS-BATCH-001.md) (Step 2a app + Step 2b platform; awaiting review/Gate 6)

**User Story**

> As an operator, I want to verify workers are processing jobs, so that I know ingestion is not stuck.

**Product Rationale**

Demo/debug requirement when ingestion appears hung.

**Functional Requirements**

- Worker heartbeat log every N minutes
- Health check includes queue depth from Redis
- Admin can see pending job count (ADMIN-002 extension)

**Acceptance Criteria**

- Given jobs in queue  
  When worker is healthy  
  Then queue depth decreases over time

**Priority:** P1  
**Dependencies:** ING-001, OBS-001  
**Notes for Engineering:** Flower for Celery optional dev tool; not required prod.

---

---

### Epic 12: Deployment and Developer Experience


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
