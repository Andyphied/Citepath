# USAGE-002 — Log Embedding Calls

> **Epic:** Epic 8: Usage Tracking and Cost Visibility  
> **Story ID:** USAGE-002
> **Status:** completed
> **Completed:** 2026-07-16
> **Implementation note:** [USAGE-002](../docs/implementation-notes/USAGE-002.md)

**User Story**

> As a Workspace Owner, I want embedding calls logged separately, so that ingestion costs are visible.

**Product Rationale**

Embedding costs dominate ingestion; separate operation type aids analysis.

**Functional Requirements**

- operation: `embedding_query`, `embedding_document`
- embedding_tokens field populated
- Linked to document_id or query context in metadata JSON

**Acceptance Criteria**

- Given document ingestion embeds 20 chunks  
  When ingestion completes  
  Then usage events record aggregate embedding tokens for the job

**Priority:** P0  
**Dependencies:** ING-004, RET-001  
**Notes for Engineering:** Batch log one event per batch call if provider returns usage once.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
