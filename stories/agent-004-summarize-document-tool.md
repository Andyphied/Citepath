# AGENT-004 — Summarize Document Tool

> **Epic:** Epic 7: AI Agent Incident Investigation  
> **Story ID:** AGENT-004
> **Status:** in_progress

**User Story**

> As the agent, I want to summarize a specific document, so that I can quickly understand long runbooks.

**Product Rationale**

Second core tool for incident workflows; read-only and workspace-scoped.

**Functional Requirements**

- Tool: `summarize_document(document_id)`
- Fetches document chunks or full text; LLM summarizes with citation to document
- Fails gracefully if document not indexed

**Acceptance Criteria**

- Given agent identifies relevant runbook document_id  
  When summarize tool is called  
  Then summary is returned and tool call is logged

**Priority:** P0  
**Dependencies:** AGENT-003, USAGE-001  
**Notes for Engineering:** Cap input tokens; summarize chunks in batches if needed.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
