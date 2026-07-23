# AGENT-002 — Agent Objective Input and Orchestration

> **Epic:** Epic 7: AI Agent Incident Investigation  
> **Story ID:** AGENT-002
> **Status:** pending

**User Story**

> As an engineer, I want to provide an incident objective, so that the agent knows what to investigate.

**Product Rationale**

Clear objective drives tool selection and structured output.

**Functional Requirements**

- Parse objective for service names, symptoms, error codes
- Agent loop: plan → tool call → observe → repeat (max steps configurable, e.g., 8)
- Terminate with structured final answer or max steps reached

**Acceptance Criteria**

- Given objective mentions "billing API 502 after deployment"  
  When agent runs  
  Then agent calls search tool with deployment and billing related queries

**Priority:** P0  
**Dependencies:** AGENT-001  
**Notes for Engineering:** Max steps prevents runaway token cost; timeout per run (e.g., 120s).


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
