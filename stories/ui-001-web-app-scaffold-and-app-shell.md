# UI-001 — Web App Scaffold and App Shell

> **Epic:** Epic 13: Minimal Demo UI  
> **Story ID:** UI-001
> **Status:** completed  
> **Completed:** 2026-07-25  
> **Implementation note:** [UI-001](../docs/implementation-notes/UI-001.md)

**User Story**

> As a demo presenter, I want a runnable web app with consistent navigation, so that I can walk through AtlasOps in a browser instead of Swagger.

**Product Rationale**

Portfolio demos need a visual surface; a shared app shell makes every feature page screenshot-ready and ties the product loop together.

**Functional Requirements**

- Next.js app (App Router) with Tailwind CSS in repo (e.g. `web/`)
- Environment config for API base URL (`NEXT_PUBLIC_API_URL`)
- Shared layout: app header, sidebar navigation, main content area
- Nav links: Documents, Ask, Agent, Admin (routes may 404 until later UI stories)
- Workspace switcher populated from `GET /workspaces`; persists active workspace (WS-006)
- Protected routes redirect unauthenticated users to login
- Typed API client module with JWT `Authorization` header injection
- `web` service added to Docker Compose (optional profile or default alongside API)
- Basic loading and error states for API failures

**Acceptance Criteria**

- Given Docker Compose is running  
  When I open the web app on port 3000  
  Then I see the AtlasOps shell with sidebar navigation

- Given I am logged in with multiple workspaces  
  When I switch workspace in the header  
  Then subsequent API calls use the selected workspace context

- Given I am not authenticated  
  When I visit `/documents`  
  Then I am redirected to `/login`

**Priority:** P1  
**Dependencies:** INFRA-001, INFRA-002, AUTH-004, AUTH-005, WS-002, WS-006  
**Notes for Engineering:** Keep styling minimal but clean (neutral palette, readable typography). No design system required. Match product name "AtlasOps AI" in header.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
