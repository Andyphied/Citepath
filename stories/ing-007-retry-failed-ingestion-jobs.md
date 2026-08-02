# ING-007 — Retry Failed Ingestion Jobs

> **Epic:** Epic 4: Ingestion Pipeline  
> **Story ID:** ING-007
> **Status:** in_progress

**User Story**

> As an Admin, I want failed ingestion jobs to be retryable, so that transient failures do not permanently block indexing.

**Product Rationale**

Retry logic demonstrates production reliability awareness.

**Functional Requirements**

- Automatic retry up to N times (e.g., 3) with exponential backoff for transient errors
- Manual retry via re-index endpoint (DOC-006) or admin action
- Store failure reason on job and document `error_message`
- Permanent failures (unsupported content, empty text) do not infinite-retry

**Acceptance Criteria**

- Given a transient embedding API timeout  
  When worker retries  
  Then job succeeds on retry and status becomes `completed`

- Given empty extracted text  
  When worker fails  
  Then job is `failed` with reason "no extractable text" and no further auto-retry

**Priority:** P1  
**Dependencies:** ING-006  
**Notes for Engineering:** Classify errors as retryable vs permanent.

---

---

### Epic 5: Vector Search and Retrieval


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
