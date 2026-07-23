# AGENT-003 — Search Knowledge Base Tool

> **Epic:** Epic 7: AI Agent Incident Investigation  
> **Story ID:** AGENT-003
> **Status:** pending

**User Story**

> As the agent, I want to search the workspace knowledge base, so that I can gather factual context before recommending actions.

**Product Rationale**

Primary agent tool; must mirror RET pipeline with workspace isolation.

**Functional Requirements**

- Tool: `search_knowledge_base(query, filters?)`
- Uses same retrieval service as RAG
- Returns chunks with citations to agent
- Logged in `agent_tool_calls`

**Acceptance Criteria**

- Given an incident investigation is started  
  When the agent needs context  
  Then it should use the knowledge base search tool before generating factual recommendations

**Priority:** P0  
**Dependencies:** RET-002, AGENT-002  
**Notes for Engineering:** Register in `ToolRegistry`; no external network calls.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
