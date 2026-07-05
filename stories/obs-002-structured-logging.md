# OBS-002 — Structured Logging

> **Epic:** Epic 11: Observability and Reliability  
> **Story ID:** OBS-002
> **Status:** in_progress

**User Story**

> As an operator, I want JSON structured logs, so that I can search and filter logs in production.

**Product Rationale**

Structured logs are baseline platform maturity.

**Functional Requirements**

- JSON log format: timestamp, level, message, request_id, workspace_id, user_id, path, duration_ms
- Log ingestion events, retrieval, LLM calls at info; errors at error

**Acceptance Criteria**

- Given an API request  
  When it completes  
  Then one structured log line includes request_id and status code

**Priority:** P1  
**Dependencies:** OBS-003  
**Notes for Engineering:** Use structlog or python-json-logger; no secrets in logs.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
