# ADMIN-001 — View Workspace Documents Overview

> **Epic:** Epic 9: Admin Dashboard  
> **Story ID:** ADMIN-001
> **Status:** in_progress

**User Story**

> As an Admin, I want an overview of documents and their statuses, so that I can see corpus health at a glance.

**Product Rationale**

Minimal admin UI/API for operational visibility.

**Functional Requirements**

- Admin endpoint or aggregated view: total documents, counts by status
- List recent uploads
- Owner and Admin only

**Acceptance Criteria**

- Given I am Admin  
  When I open admin documents view  
  Then I see document counts by status

- Given I am Viewer  
  When I access admin endpoints  
  Then the API returns 403

**Priority:** P1  
**Dependencies:** DOC-003, WS-005  
**Notes for Engineering:** Can reuse document list with summary header.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
