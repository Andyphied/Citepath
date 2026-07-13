# INFRA-005 — GitHub Actions CI

> **Epic:** Epic 12: Deployment and Developer Experience  
> **Story ID:** INFRA-005
> **Status:** completed
> **Completed:** 2026-07-13
> **Implementation note:** [INFRA-005](../docs/implementation-notes/INFRA-005.md)

**User Story**

> As a developer, I want CI to run tests and lint on every push, so that regressions are caught early.

**Product Rationale**

CI demonstrates engineering maturity for portfolio reviewers.

**Functional Requirements**

- Workflow: lint (ruff/black), type check (mypy optional), unit tests, integration tests with test DB
- Runs on PR and main push

**Acceptance Criteria**

- Given failing test  
  When PR is opened  
  Then CI fails

**Priority:** P1  
**Dependencies:** INFRA-003  
**Notes for Engineering:** Use service containers for Postgres in CI.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
