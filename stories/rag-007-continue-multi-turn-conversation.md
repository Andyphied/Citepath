# RAG-007 — Continue Multi-Turn Conversation

> **Epic:** Epic 6: RAG Question Answering  
> **Story ID:** RAG-007
> **Status:** in_progress

**User Story**

> As an engineer, I want to ask follow-up questions in the same conversation, so that I can drill down without repeating context.

**Product Rationale**

Multi-turn is expected chat UX and demonstrates conversation model design.

**Functional Requirements**

- Pass `conversation_id` on subsequent queries
- Include recent history in prompt (not full corpus re-retrieval only — re-retrieve each turn)
- Each turn logs separate usage event

**Acceptance Criteria**

- Given an existing conversation  
  When I ask a follow-up  
  Then the answer considers prior turns and new retrieval

**Priority:** P1  
**Dependencies:** RAG-006  
**Notes for Engineering:** Re-run retrieval each turn; do not rely solely on prior assistant text.

---

---

### Epic 7: AI Agent Incident Investigation


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
