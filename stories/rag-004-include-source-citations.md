# RAG-004 — Include Source Citations

> **Epic:** Epic 6: RAG Question Answering  
> **Story ID:** RAG-004
> **Status:** completed
> **Completed:** 2026-07-23
> **Implementation note:** [RAG-004](../docs/implementation-notes/RAG-004.md)

**User Story**

> As an engineer, I want answers to include citations from retrieved document chunks, so that I can verify the assistant's claims.

**Product Rationale**

Citations are a non-negotiable trust mechanism for operational AI.

**Functional Requirements**

- Response includes `citations[]` with document id, title, chunk id, preview, optional page/section
- Inline citation markers in answer text optional (e.g., [1], [2])
- Each factual claim should map to at least one citation when context supports it

**Acceptance Criteria**

- Given an answer is generated  
  When response is returned  
  Then `citations` array is non-empty when context was used

- Given citation in response  
  When I inspect it  
  Then I see document title and chunk preview

**Priority:** P0  
**Dependencies:** RAG-003, RET-005  
**Notes for Engineering:** Store citations on assistant message record.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
