# UI-005 — Agent Investigation Page

> **Epic:** Epic 13: Minimal Demo UI  
> **Story ID:** UI-005
> **Status:** completed  
> **Completed:** 2026-07-29  
> **Implementation note:** [UI-005](../docs/implementation-notes/UI-005.md)

**User Story**

> As an engineer, I want to run an incident agent investigation in the web app, so that I can show structured AI-assisted debugging in a demo.

**Product Rationale**

The agent page differentiates AtlasOps from simple chatbots; structured output sections make a compelling second hero screenshot.

**Functional Requirements**

- `/agent` page within app shell
- Objective textarea (incident description) and "Start investigation" button
- Calls `POST /workspaces/{id}/agent-runs`; polls or waits for completion (sync acceptable for MVP)
- Running state: progress indicator, disable duplicate submits
- On completion, render AGENT-008 structured sections:
  - Summary
  - Likely related systems
  - Relevant documents
  - Suggested checks
  - Risks / unknowns
  - Sources
  - Next steps
- Sources section links or lists cited documents
- Error state if agent run fails or times out

**Acceptance Criteria**

- Given indexed demo documents  
  When I start an investigation for a billing 502 incident  
  Then I see all structured sections populated after the run completes

- Given the agent is running  
  When I view the page  
  Then the start button is disabled and a loading indicator is visible

- Given the agent completes  
  When I inspect Sources  
  Then cited documents match the structured output content

**Priority:** P1  
**Dependencies:** UI-001, UI-002, AGENT-001, AGENT-008  
**Notes for Engineering:** Use section headings matching API field names. Card-based layout works well for screenshots. Timeout UI after ~120s with retry option.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
