# RAG-002 — Retrieve Context for Question

> **Epic:** Epic 6: RAG Question Answering  
> **Story ID:** RAG-002
> **Status:** in_progress

**User Story**

> As the system, I want to retrieve relevant chunks before generating an answer, so that responses are grounded in internal docs.

**Product Rationale**

Retrieval-before-generation is the defining RAG pattern.

**Functional Requirements**

- Call retrieval service with question embedding
- Select top 4–5 chunks for LLM context after initial k=8 retrieval
- Pass chunk text and citation metadata to prompt builder

**Acceptance Criteria**

- Given relevant runbook exists  
  When question mentions billing 502  
  Then billing runbook chunks appear in retrieved context

**Priority:** P0  
**Dependencies:** RET-003  
**Notes for Engineering:** Optional lightweight rerank P2; MVP can use score-only selection.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
