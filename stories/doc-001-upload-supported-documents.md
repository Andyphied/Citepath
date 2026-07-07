# DOC-001 — Upload Supported Documents

> **Epic:** Epic 3: Document Upload and Management  
> **Story ID:** DOC-001
> **Status:** completed
> **Completed:** 2026-07-07
> **Implementation note:** [DOC-001](../docs/implementation-notes/DOC-001.md)

**User Story**

> As an Admin, I want to upload engineering documents, so that AtlasOps can index my team's knowledge.

**Product Rationale**

Upload is the first step in the core product loop; without documents, RAG and agents have nothing to retrieve.

**Functional Requirements**

- `POST /workspaces/{workspace_id}/documents` multipart upload
- Supported types: `.md`, `.txt`, `.pdf`, `.json`
- Max file size configurable (e.g., 10 MB MVP default)
- Stores file to object storage; creates document record with status `uploaded`
- Fields: `title` (default filename), `source_type`, `file_type`, `uploaded_by`, `workspace_id`
- Triggers ingestion job creation (ING-001)
- Requires Admin, Member, or higher (not Viewer)

**Acceptance Criteria**

- Given I upload `billing-api-runbook.md`  
  When upload completes  
  Then document is saved with status `uploaded` and assigned to my workspace

- Given I upload an unsupported `.exe` file  
  When upload completes  
  Then the API returns 422 with unsupported file type error

**Priority:** P0  
**Dependencies:** WS-005, WS-006  
**Notes for Engineering:** Validate MIME type and extension; virus scan out of scope.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
