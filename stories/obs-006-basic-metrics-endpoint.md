# OBS-006 — Basic Metrics Endpoint

> **Epic:** Epic 11: Observability and Reliability  
> **Story ID:** OBS-006
> **Status:** in_progress

**User Story**

> As an operator, I want basic internal metrics, so that I can monitor latency and error rates.

**Product Rationale**

Portfolio cloud readiness; Prometheus-compatible optional.

**Functional Requirements**

- `GET /metrics` (internal/auth optional) or expose counters via structured logs
- Counters: http_requests_total, http_errors_total, ingestion_jobs_total, llm_calls_total
- Histograms optional P2

**Acceptance Criteria**

- Given traffic flows through API  
  When metrics endpoint is scraped  
  Then request counts increment

**Priority:** P2  
**Dependencies:** OBS-002  
**Notes for Engineering:** prometheus_client if easy; else document log-based metrics.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
