# RET-004 — Metadata Filtering

> **Epic:** Epic 5: Vector Search and Retrieval  
> **Story ID:** RET-004
> **Status:** completed
> **Completed:** 2026-07-23
> **Implementation note:** [RET-004](../docs/implementation-notes/RET-004.md)

**User Story**

> As an engineer, I want to filter retrieval by document type or source, so that answers focus on runbooks or incidents.

**Product Rationale**

Metadata filters improve precision for agent tools and power-user queries.

**Functional Requirements**

- Optional filters: `file_type`, `source_type`, `document_id`
- Filters applied in SQL alongside workspace_id
- Agent search tool accepts filter parameters

**Acceptance Criteria**

- Given filter `file_type=pdf`  
  When search runs  
  Then only PDF document chunks are returned

**Priority:** P1  
**Dependencies:** RET-002  
**Notes for Engineering:** Index filter columns; validate filter values.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
