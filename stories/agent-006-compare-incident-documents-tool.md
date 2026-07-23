# AGENT-006 — Compare Incident Documents Tool

> **Epic:** Epic 7: AI Agent Incident Investigation  
> **Story ID:** AGENT-006
> **Status:** pending

**User Story**

> As the agent, I want to compare multiple incident documents, so that I can identify recurring patterns.

**Product Rationale**

Supports "recurring causes" demo scenario; shows multi-document reasoning.

**Functional Requirements**

- Tool: `compare_incidents(document_ids[])` (2–5 documents)
- Validates all documents in same workspace
- Returns similarities, differences, recurring themes

**Acceptance Criteria**

- Given two billing incident documents  
  When compare tool runs  
  Then output highlights common root causes with citations

**Priority:** P1  
**Dependencies:** AGENT-003  
**Notes for Engineering:** MVP can pass document IDs from search results.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
