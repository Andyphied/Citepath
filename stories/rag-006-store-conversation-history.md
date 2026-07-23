# RAG-006 — Store Conversation History

> **Epic:** Epic 6: RAG Question Answering  
> **Story ID:** RAG-006
> **Status:** in_progress

**User Story**

> As an engineer, I want my questions and answers saved, so that I can review past investigations.

**Product Rationale**

Conversation history supports multi-turn debugging and admin visibility.

**Functional Requirements**

- `conversations` table: id, workspace_id, user_id, title, mode (`rag`), created_at
- `messages` table: role (user/assistant), content, citations, metadata, created_at
- Auto-title conversation from first question (truncated)
- `GET /workspaces/{workspace_id}/conversations` and detail endpoint

**Acceptance Criteria**

- Given I ask a follow-up in same conversation_id  
  When answer is generated  
  Then prior messages are available for context (last N turns)

- Given I list conversations  
  When I open one  
  Then I see full message history with citations

**Priority:** P0  
**Dependencies:** RAG-001  
**Notes for Engineering:** Limit context window to last 5 turns for LLM; store full history in DB.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
