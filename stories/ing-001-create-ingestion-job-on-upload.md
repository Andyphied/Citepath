# ING-001 — Create Ingestion Job on Upload

> **Epic:** Epic 4: Ingestion Pipeline  
> **Story ID:** ING-001
> **Status:** completed
> **Completed:** 2026-07-07
> **Implementation note:** [ING-001](../docs/implementation-notes/ING-001.md)

**User Story**

> As the system, I want to enqueue an ingestion job when a document is uploaded, so that processing happens asynchronously.

**Product Rationale**

Background processing is a production requirement; synchronous ingestion blocks API and fails at scale.

**Functional Requirements**

- On document upload, create `ingestion_jobs` record with status `pending`
- Enqueue Celery/RQ task with `document_id`, `workspace_id`
- Update document status to `processing` when worker picks up job

**Acceptance Criteria**

- Given a successful upload  
  When the API responds  
  Then an ingestion job exists with status `pending` or `processing`

**Priority:** P0  
**Dependencies:** DOC-001  
**Notes for Engineering:** Job payload must include workspace_id for isolation checks in worker.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
