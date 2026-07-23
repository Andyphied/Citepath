# AGENT-001 — Start Agent Investigation

> **Epic:** Epic 7: AI Agent Incident Investigation  
> **Story ID:** AGENT-001
> **Status:** in_progress

**User Story**

> As an engineer, I want to start an incident investigation session, so that the AI agent can help me debug systematically.

**Product Rationale**

Agent mode is the second major MVP capability alongside RAG; demonstrates tool-calling architecture.

**Functional Requirements**

- `POST /workspaces/{workspace_id}/agent-runs` accepts `objective` (incident description), optional `conversation_id`
- Creates `agent_runs` record with status `running`
- Mode distinct from RAG (`mode: incident`)
- All roles except Viewer restrictions same as RAG (Viewer can run agent — clarify: PRD says Viewer can ask questions; include agent for Engineer+ — **Viewer can ask questions per persona; agent investigation for Member+**)

**Acceptance Criteria**

- Given I describe a billing 502 incident  
  When I start agent run  
  Then agent_run is created with status `running` and my objective stored

**Priority:** P0  
**Dependencies:** WS-005, RAG-006  
**Notes for Engineering:** Viewer: read-only on docs but can ask/agent per PRD Engineer persona; **allow Viewer to run agent** since they can "ask questions" — restrict only doc mutations.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
