# ADMIN-004 — View Usage Summary (Dashboard)

> **Epic:** Epic 9: Admin Dashboard  
> **Story ID:** ADMIN-004
> **Status:** in_progress

**User Story**

> As a Workspace Owner, I want usage on the admin dashboard, so that I can monitor token spend.

**Product Rationale**

Connects USAGE epic to user-facing admin experience.

**Functional Requirements**

- Dashboard section calling USAGE-004 endpoint
- Show 7-day totals and estimated cost

**Acceptance Criteria**

- Given usage events exist  
  When Owner opens admin dashboard  
  Then usage summary displays non-zero totals

**Priority:** P1  
**Dependencies:** USAGE-004  
**Notes for Engineering:** Simple table sufficient; no charts required.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
