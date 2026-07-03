# INFRA-003 — Database Migrations

> **Epic:** Epic 12: Deployment and Developer Experience  
> **Story ID:** INFRA-003
> **Status:** in_progress

**User Story**

> As a developer, I want versioned database migrations, so that schema changes are reproducible.

**Product Rationale**

Alembic migrations show production database discipline.

**Functional Requirements**

- Alembic setup with initial migration for all core tables
- Migration runs on deploy or via documented command
- pgvector extension in migration

**Acceptance Criteria**

- Given empty database  
  When migrations run  
  Then all tables from data model exist

**Priority:** P0  
**Dependencies:** None  
**Notes for Engineering:** Include indexes for workspace_id on all tenant tables.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
