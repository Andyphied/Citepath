# OBS-005 — Ingestion Failure Handling

> **Epic:** Epic 11: Observability and Reliability  
> **Story ID:** OBS-005
> **Status:** in_progress  
> **Implementation note:** [OBS-BATCH-001](../docs/implementation-notes/OBS-BATCH-001.md) (Step 2a; batch not Gate-6 complete)

**User Story**

> As an operator, I want ingestion failures logged with context, so that I can diagnose worker issues.

**Product Rationale**

Background job failures are common; visibility prevents silent breakage.

**Functional Requirements**

- Worker logs document_id, workspace_id, job_id, error stack on failure
- Update job and document status atomically
- Metrics: ingestion_duration_seconds, ingestion_failures_total (OBS-006)

**Acceptance Criteria**

- Given extraction failure  
  When worker catches error  
  Then structured error log is emitted and job marked failed

**Priority:** P1  
**Dependencies:** ING-007, OBS-002  
**Notes for Engineering:** Celery task acks late; idempotent retries.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
