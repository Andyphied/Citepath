# RAG-001 — Ask a Question

> **Epic:** Epic 6: RAG Question Answering  
> **Story ID:** RAG-001
> **Status:** in_progress

**User Story**

> As an engineer, I want to ask a natural-language question, so that I get answers from my team's documentation.

**Product Rationale**

Core user-facing value; central to the product loop.

**Functional Requirements**

- `POST /workspaces/{workspace_id}/query` accepts `question`, optional `conversation_id`
- Creates conversation if new; appends user message
- Triggers retrieval → answer generation pipeline
- All roles including Viewer can ask

**Acceptance Criteria**

- Given indexed documents  
  When I ask "What should I check for billing 502 errors?"  
  Then I receive an answer within acceptable latency (< 30s MVP target)

**Priority:** P0  
**Dependencies:** RET-003, RAG-003  
**Notes for Engineering:** Async optional P2; sync response acceptable for MVP.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
