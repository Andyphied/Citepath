# INFRA-007 — README and Architecture Documentation

> **Epic:** Epic 12: Deployment and Developer Experience  
> **Story ID:** INFRA-007
> **Status:** in_progress

**User Story**

> As a portfolio reviewer, I want clear README and architecture docs, so that I understand design decisions quickly.

**Product Rationale**

Documentation is part of MVP deliverable per PRD acceptance criteria.

**Functional Requirements**

- README: overview, local setup, env vars, API link, testing, security notes, tradeoffs
- Architecture diagram (Mermaid or PNG): API, worker, DB, vector store, LLM provider
- Design decisions: pgvector vs dedicated vector DB, JWT auth, chunking strategy

**Acceptance Criteria**

- Given new reviewer  
  When they read README  
  Then they can start local stack and run demo query in < 30 min

**Priority:** P1  
**Dependencies:** INFRA-001, INFRA-004  
**Notes for Engineering:** Include workspace isolation section prominently.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
