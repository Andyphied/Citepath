# DOC-007 — Document Status Display

> **Epic:** Epic 3: Document Upload and Management  
> **Story ID:** DOC-007
> **Status:** in_progress

**User Story**

> As a user, I want clear document status values, so that I understand ingestion progress.

**Product Rationale**

Status enum is the user-facing contract for async processing.

**Functional Requirements**

- Status values: `uploaded`, `processing`, `indexed`, `failed`
- Status transitions driven by ingestion worker
- UI/API exposes human-readable status labels

**Acceptance Criteria**

- Given upload completes  
  When ingestion starts  
  Then status becomes `processing`

- Given ingestion succeeds  
  When worker completes  
  Then status becomes `indexed`

**Priority:** P0  
**Dependencies:** ING-001  
**Notes for Engineering:** Document state machine in code comments or enum.

---

---

### Epic 4: Ingestion Pipeline


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
