# RET-003 — Top-K Retrieval with Scores

> **Epic:** Epic 5: Vector Search and Retrieval  
> **Story ID:** RET-003
> **Status:** in_progress

**User Story**

> As the system, I want to return top-k chunks with similarity scores, so that downstream RAG can rank and cite sources.

**Product Rationale**

Scores enable confidence heuristics and citation ordering.

**Functional Requirements**

- Return chunk id, content preview, score, document metadata, citation_id
- Default k=8; compress to top 4–5 for LLM context in RAG layer
- Minimum score threshold optional; below threshold triggers insufficient-context path

**Acceptance Criteria**

- Given indexed documents  
  When I search with a relevant query  
  Then I receive up to 8 chunks ordered by descending score

- Given no chunks above threshold  
  When search completes  
  Then empty or low-score result set is flagged to RAG layer

**Priority:** P0  
**Dependencies:** RET-002  
**Notes for Engineering:** `citation_id` stable for UI linking; can be chunk UUID.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
