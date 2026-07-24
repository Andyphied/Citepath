# USAGE-003 — Cost Estimation

> **Epic:** Epic 8: Usage Tracking and Cost Visibility  
> **Story ID:** USAGE-003
> **Status:** in_progress

**User Story**

> As a Workspace Owner, I want estimated costs per call, so that I can rough projected spend.

**Product Rationale**

Dollar estimates make usage tangible in demos without building billing.

**Functional Requirements**

- Config table or env vars for price per 1K tokens by model
- `estimated_cost` on each usage_event
- Document assumptions in README (estimates not invoices)

**Acceptance Criteria**

- Given a logged LLM call with known token counts  
  When cost is calculated  
  Then `estimated_cost` is populated using configured rates

**Priority:** P1  
**Dependencies:** USAGE-001  
**Notes for Engineering:** Use Decimal for money; 6 decimal places sufficient.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
