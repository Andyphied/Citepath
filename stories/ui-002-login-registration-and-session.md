# UI-002 — Login, Registration, and Session

> **Epic:** Epic 13: Minimal Demo UI  
> **Story ID:** UI-002  
> **Status:** in_progress  
> **Implementation note (draft):** [UI-002](../docs/implementation-notes/UI-002.md)

**User Story**

> As a user, I want to register and log in through the web app, so that I can access my workspace without using API tools.

**Product Rationale**

Auth is the first step in every demo and portfolio screenshot set; a dedicated login screen establishes product credibility.

**Functional Requirements**

- `/login` page: email, password, submit; link to register
- `/register` page: email, password, confirm password (client-side), submit
- On successful login/register, store JWT securely (httpOnly cookie preferred; localStorage acceptable for MVP demo)
- Call `GET /auth/me` on app load to bootstrap session and display user name/email in header
- Logout button calls `POST /auth/logout` and clears session; redirects to `/login`
- Display auth errors from API (401, validation errors) inline
- After login, redirect to first workspace or workspace creation prompt if none exist

**Acceptance Criteria**

- Given valid credentials  
  When I submit the login form  
  Then I land on the app shell with my email shown in the header

- Given invalid password  
  When I submit the login form  
  Then I see an error message and remain on `/login`

- Given I click Logout  
  When session clears  
  Then I am redirected to `/login` and protected routes are inaccessible

**Priority:** P1  
**Dependencies:** UI-001, AUTH-001, AUTH-002, AUTH-003, AUTH-004, AUTH-006  
**Notes for Engineering:** Login page is a primary portfolio screenshot — center the form, use product logo/title. No OAuth or password reset in MVP.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
