# UI-003 — Documents Page

> **Epic:** Epic 13: Minimal Demo UI  
> **Story ID:** UI-003
> **Status:** completed  
> **Completed:** 2026-07-28  
> **Implementation note:** [UI-003](../docs/implementation-notes/UI-003.md)

**User Story**

> As an Admin, I want to upload and monitor documents in the web app, so that I can show the ingest loop visually during a demo.

**Product Rationale**

Document upload with live status badges is a core portfolio screenshot — it proves the workspace → upload → index loop.

**Functional Requirements**

- `/documents` page within app shell
- File upload control (drag-and-drop or file picker) calling `POST /workspaces/{id}/documents`
- Document table: title, file type, status badge, uploaded date, uploaded by
- Status badges map to API values: `uploaded`, `processing`, `indexed`, `failed` (human-readable labels per DOC-007)
- Poll or refresh list while any document is `processing`
- Show upload progress and success/error toasts
- Empty state when no documents ("Upload your first runbook")
- Hide upload control for Viewer role (read-only list or message)

**Acceptance Criteria**

- Given I upload `billing-api-runbook.md`  
  When upload completes  
  Then the document appears in the table with status `uploaded` or `processing`

- Given a document finishes indexing  
  When I view the documents page  
  Then its status badge shows `indexed`

- Given I am a Viewer  
  When I open `/documents`  
  Then I see the list but no upload control

**Priority:** P1  
**Dependencies:** UI-001, UI-002, DOC-001, DOC-003, DOC-007, WS-005  
**Notes for Engineering:** Status badge colors (gray/yellow/green/red) make this page demo-friendly. Table screenshot should show at least 2–3 Northstar demo documents.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
