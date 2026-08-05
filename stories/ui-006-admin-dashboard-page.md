# UI-006 — Admin Dashboard Page

> **Epic:** Epic 13: Minimal Demo UI  
> **Story ID:** UI-006
> **Status:** in_progress

**User Story**

> As an Admin, I want an admin dashboard in the web app, so that I can show operational visibility during the demo closing act.

**Product Rationale**

The admin dashboard screenshot proves the platform story — ingestion health, usage, and corpus status beyond chat.

**Functional Requirements**

- `/admin` page within app shell; visible in nav only for Owner/Admin roles (WS-005)
- Summary cards row:
  - Document counts by status (ADMIN-001)
  - Token usage totals and estimated cost, 7-day window (ADMIN-004)
  - Failed jobs count (ADMIN-005)
- Ingestion jobs table: document title, status, started/completed time, error message if failed (ADMIN-002)
- Recent uploads list (from ADMIN-001 or DOC-003)
- Non-admin users see 403 message or hidden nav item
- Empty states when no data yet

**Acceptance Criteria**

- Given I am Admin with indexed documents and usage events  
  When I open `/admin`  
  Then I see document status counts and non-zero usage summary

- Given a failed ingestion job exists  
  When I view the dashboard  
  Then the failed jobs section highlights it with the error message

- Given I am a Viewer  
  When I attempt to access `/admin`  
  Then I see an access denied message or am redirected

**Priority:** P1  
**Dependencies:** UI-001, UI-002, ADMIN-001, ADMIN-002, ADMIN-004, ADMIN-005, WS-005  
**Notes for Engineering:** Simple stat cards + tables — no charts required. Dashboard screenshot should show healthy corpus (mostly `indexed`) after Northstar seed.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
