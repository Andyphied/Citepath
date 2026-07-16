# DOC-002 — File Type Validation

> **Epic:** Epic 3: Document Upload and Management  
> **Story ID:** DOC-002
> **Status:** completed
> **Completed:** 2026-07-16
> **Implementation note:** [DOC-002](../docs/implementation-notes/DOC-002.md)

**User Story**

> As the system, I want to reject unsupported file types at upload, so that ingestion failures are prevented early.

**Product Rationale**

Fail fast at upload reduces wasted worker cycles and clearer user feedback.

**Functional Requirements**

- Whitelist extensions: md, txt, pdf, json
- Reject empty files
- Return validation error with allowed types list

**Acceptance Criteria**

- Given a `.docx` file  
  When I attempt upload  
  Then the API returns 422 before storage

**Priority:** P0  
**Dependencies:** DOC-001  
**Notes for Engineering:** PDF validation can check magic bytes `%PDF`.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
