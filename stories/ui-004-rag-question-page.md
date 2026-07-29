# UI-004 — RAG Question Page

> **Epic:** Epic 13: Minimal Demo UI  
> **Story ID:** UI-004
> **Status:** completed  
> **Completed:** 2026-07-29  
> **Implementation note:** [UI-004](../docs/implementation-notes/UI-004.md)

**User Story**

> As an engineer, I want to ask questions and see cited answers in the web app, so that I can demonstrate grounded RAG during a live demo.

**Product Rationale**

The Q&A screen with citations is the hero portfolio screenshot — it shows the product's core value visually.

**Functional Requirements**

- `/ask` page within app shell
- Question input (textarea) and submit button
- Loading state while answer generates (spinner + "Searching knowledge base…")
- Answer display area with formatted text/markdown rendering
- Citations panel: document title, chunk preview, optional page/section; expandable/collapsible
- Conversation thread: show prior Q&A pairs in session when `conversation_id` is returned
- Follow-up questions append to same conversation (RAG-007)
- Handle insufficient-context responses with distinct styling (RAG-005)
- Pre-fill demo question optional via query param (e.g. `?q=billing+502`) for repeatable screenshots

**Acceptance Criteria**

- Given indexed Northstar demo documents  
  When I ask "What should I check for billing 502 errors?"  
  Then I see an answer with at least one citation referencing uploaded docs

- Given I submit a follow-up in the same session  
  When the answer returns  
  Then both turns appear in the conversation thread

- Given retrieval returns weak context  
  When the answer is insufficient  
  Then the UI shows the API's insufficient-context message clearly (not a generic error)

**Priority:** P1  
**Dependencies:** UI-001, UI-002, RAG-001, RAG-004, RAG-005, RAG-007  
**Notes for Engineering:** Primary screenshot target — use a two-column or stacked layout (question → answer → citations). Non-streaming: disable submit until response completes.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
