# AGENT-007 — Suggest Debugging Steps Tool

> **Epic:** Epic 7: AI Agent Incident Investigation  
> **Story ID:** AGENT-007
> **Status:** pending

**User Story**

> As the agent, I want to suggest debugging steps based on service and symptom, so that engineers have a practical checklist.

**Product Rationale**

Operational utility tool; must still cite runbooks when suggesting steps.

**Functional Requirements**

- Tool: `suggest_debugging_steps(service_name, symptom)`
- Internally searches knowledge base for service + symptom
- Returns numbered checks grounded in retrieved docs; labels speculative steps clearly

**Acceptance Criteria**

- Given service "billing-api" and symptom "502"  
  When tool runs  
  Then suggested checks reference retrieved runbook content

**Priority:** P0  
**Dependencies:** AGENT-003  
**Notes for Engineering:** Do not present generic steps as internal facts without sources.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
