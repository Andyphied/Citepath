# AGENT-008 — Structured Final Agent Answer

> **Epic:** Epic 7: AI Agent Incident Investigation  
> **Story ID:** AGENT-008
> **Status:** pending

**User Story**

> As an engineer, I want a structured investigation summary, so that I can act on results quickly during an incident.

**Product Rationale**

Structured output is the deliverable of agent mode; must match PRD schema.

**Functional Requirements**

Final JSON/markdown structure:

- Summary
- Likely related systems
- Relevant documents
- Suggested checks
- Risks / unknowns
- Sources
- Next steps

- Stored on `agent_runs.final_answer`; status → `completed`
- All factual sections cite sources

**Acceptance Criteria**

- Given agent completes investigation  
  When I fetch agent run  
  Then response includes all required sections

- Given agent makes factual claim about internal service  
  When I inspect sources  
  Then claim maps to retrieved document citation

**Priority:** P0  
**Dependencies:** AGENT-002, AGENT-003  
**Notes for Engineering:** Validate output schema; fallback partial answer on max steps.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
