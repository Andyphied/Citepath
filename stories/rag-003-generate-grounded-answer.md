# RAG-003 — Generate Grounded Answer

> **Epic:** Epic 6: RAG Question Answering  
> **Story ID:** RAG-003
> **Status:** in_progress

**User Story**

> As an engineer, I want answers based only on retrieved context, so that I can trust operational guidance.

**Product Rationale**

Grounding reduces hallucination risk; portfolio-critical behavior.

**Functional Requirements**

- Prompt instructs model to answer only from provided context
- Separate facts from recommendations in response structure
- Include confidence indicator (high/medium/low based on retrieval scores)
- Suggest 2–3 follow-up questions

**Acceptance Criteria**

- Given strong retrieval matches  
  When answer is generated  
  Then answer references facts present in retrieved chunks

- Given the retrieved context does not contain enough information  
  When the assistant generates an answer  
  Then it states that it could not find enough context instead of inventing an answer

**Priority:** P0  
**Dependencies:** RAG-002, USAGE-001  
**Notes for Engineering:** System prompt must forbid inventing service names; log prompt version string.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
