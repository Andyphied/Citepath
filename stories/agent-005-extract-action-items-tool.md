# AGENT-005 — Extract Action Items Tool

> **Epic:** Epic 7: AI Agent Incident Investigation  
> **Story ID:** AGENT-005
> **Status:** pending

**User Story**

> As the agent, I want to extract action items from incident documents, so that I can suggest concrete next steps.

**Product Rationale**

Demonstrates structured extraction tool pattern common in ops workflows.

**Functional Requirements**

- Tool: `extract_action_items(document_id)`
- Returns list of action items with source references
- LLM extracts from document content only

**Acceptance Criteria**

- Given incident postmortem document  
  When tool runs  
  Then action items list is returned with document citation

**Priority:** P0  
**Dependencies:** AGENT-004  
**Notes for Engineering:** Output JSON schema for parsing.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
