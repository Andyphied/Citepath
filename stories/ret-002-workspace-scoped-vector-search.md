# RET-002 — Workspace-Scoped Vector Search

> **Epic:** Epic 5: Vector Search and Retrieval  
> **Story ID:** RET-002
> **Status:** completed
> **Completed:** 2026-07-22
> **Implementation note:** [RET-002](../docs/implementation-notes/RET-002.md)

**User Story**

> As an engineer, I want search results limited to my workspace, so that I never see another team's documents.

**Product Rationale**

Non-negotiable security requirement; must be tested explicitly.

**Functional Requirements**

- Similarity search filtered by `workspace_id`
- Cosine similarity or L2 per pgvector config
- Return top-k results (default k=8)

**Acceptance Criteria**

- Given I belong to Workspace A  
  When I ask a question in Workspace A  
  Then retrieval only searches documents belonging to Workspace A

- Given identical content in Workspace A and B  
  When User A searches  
  Then only Workspace A chunks appear

**Priority:** P0  
**Dependencies:** ING-005, WS-007  
**Notes for Engineering:** SQL must include `WHERE workspace_id = :id`; never rely on post-filter.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
