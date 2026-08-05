# AtlasOps AI — MVP User Stories

Individual story files extracted from [MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md).

**Total stories:** 85

## Story status

Each story file includes a **Status** field in its metadata block:

| Status | Meaning |
|--------|---------|
| `pending` | Not started (default) |
| `in_progress` | Implementation underway |
| `completed` | Implemented, reviewed, and accepted |
| `blocked` | Cannot proceed — dependency or decision missing |

When a story is **completed**, the metadata also includes:

- **Completed:** date (`YYYY-MM-DD`)
- **Implementation note:** link to `docs/implementation-notes/STORY-ID.md`

Update the story file when status changes (see `.cursor/skills/atlasops-mvp-delivery/SKILL.md`):

- **Gate 1:** phase planner recommends story + implementation plan (single or sequence); human approves
- **`in_progress`:** first implementer in the approved plan
- **`completed`:** last implementer in the approved plan at Gate 6

To check progress: `rg '^\> \*\*Status:\*\* completed' stories/ | wc -l`

## Story Index

### Epic 1: Authentication and User Accounts

- [AUTH-001 — User Registration](./auth-001-user-registration.md)
- [AUTH-002 — User Login](./auth-002-user-login.md)
- [AUTH-003 — User Logout](./auth-003-user-logout.md)
- [AUTH-004 — Current User Endpoint](./auth-004-current-user-endpoint.md)
- [AUTH-005 — JWT Authentication Middleware](./auth-005-jwt-authentication-middleware.md)
- [AUTH-006 — Auth Error Responses](./auth-006-auth-error-responses.md)

### Epic 2: Workspace Management and RBAC

- [WS-001 — Create Workspace](./ws-001-create-workspace.md)
- [WS-002 — List and Get Workspaces](./ws-002-list-and-get-workspaces.md)
- [WS-003 — Invite and Manage Members](./ws-003-invite-and-manage-members.md)
- [WS-004 — Change Member Roles and Remove Members](./ws-004-change-member-roles-and-remove-members.md)
- [WS-005 — Role-Based Permission Matrix](./ws-005-role-based-permission-matrix.md)
- [WS-006 — Active Workspace Context](./ws-006-active-workspace-context.md)
- [WS-007 — Workspace-Scoped Data Access Layer](./ws-007-workspace-scoped-data-access-layer.md)

### Epic 3: Document Upload and Management

- [DOC-001 — Upload Supported Documents](./doc-001-upload-supported-documents.md)
- [DOC-002 — File Type Validation](./doc-002-file-type-validation.md)
- [DOC-003 — List Documents](./doc-003-list-documents.md)
- [DOC-004 — View Document Details](./doc-004-view-document-details.md)
- [DOC-005 — Delete Document](./doc-005-delete-document.md)
- [DOC-006 — Re-index Document](./doc-006-re-index-document.md)
- [DOC-007 — Document Status Display](./doc-007-document-status-display.md)

### Epic 4: Ingestion Pipeline

- [ING-001 — Create Ingestion Job on Upload](./ing-001-create-ingestion-job-on-upload.md)
- [ING-002 — Extract Text from Documents](./ing-002-extract-text-from-documents.md)
- [ING-003 — Chunk Document Content](./ing-003-chunk-document-content.md)
- [ING-004 — Generate Embeddings for Chunks](./ing-004-generate-embeddings-for-chunks.md)
- [ING-005 — Store Chunks in Vector Database](./ing-005-store-chunks-in-vector-database.md)
- [ING-006 — Track Ingestion Job Status](./ing-006-track-ingestion-job-status.md)
- [ING-007 — Retry Failed Ingestion Jobs](./ing-007-retry-failed-ingestion-jobs.md)

### Epic 5: Vector Search and Retrieval

- [RET-001 — Generate Query Embedding](./ret-001-generate-query-embedding.md)
- [RET-002 — Workspace-Scoped Vector Search](./ret-002-workspace-scoped-vector-search.md)
- [RET-003 — Top-K Retrieval with Scores](./ret-003-top-k-retrieval-with-scores.md)
- [RET-004 — Metadata Filtering](./ret-004-metadata-filtering.md)
- [RET-005 — Source Chunk Preview](./ret-005-source-chunk-preview.md)

### Epic 6: RAG Question Answering

- [RAG-001 — Ask a Question](./rag-001-ask-a-question.md)
- [RAG-002 — Retrieve Context for Question](./rag-002-retrieve-context-for-question.md)
- [RAG-003 — Generate Grounded Answer](./rag-003-generate-grounded-answer.md)
- [RAG-004 — Include Source Citations](./rag-004-include-source-citations.md)
- [RAG-005 — Insufficient Context Response](./rag-005-insufficient-context-response.md)
- [RAG-006 — Store Conversation History](./rag-006-store-conversation-history.md)
- [RAG-007 — Continue Multi-Turn Conversation](./rag-007-continue-multi-turn-conversation.md)

### Epic 7: AI Agent Incident Investigation

- [AGENT-001 — Start Agent Investigation](./agent-001-start-agent-investigation.md)
- [AGENT-002 — Agent Objective Input and Orchestration](./agent-002-agent-objective-input-and-orchestration.md)
- [AGENT-003 — Search Knowledge Base Tool](./agent-003-search-knowledge-base-tool.md)
- [AGENT-004 — Summarize Document Tool](./agent-004-summarize-document-tool.md)
- [AGENT-005 — Extract Action Items Tool](./agent-005-extract-action-items-tool.md)
- [AGENT-006 — Compare Incident Documents Tool](./agent-006-compare-incident-documents-tool.md)
- [AGENT-007 — Suggest Debugging Steps Tool](./agent-007-suggest-debugging-steps-tool.md)
- [AGENT-008 — Structured Final Agent Answer](./agent-008-structured-final-agent-answer.md)
- [AGENT-009 — Log Agent Tool Calls](./agent-009-log-agent-tool-calls.md)

### Epic 8: Usage Tracking and Cost Visibility

- [USAGE-001 — Log LLM Completion Calls](./usage-001-log-llm-completion-calls.md)
- [USAGE-002 — Log Embedding Calls](./usage-002-log-embedding-calls.md)
- [USAGE-003 — Cost Estimation](./usage-003-cost-estimation.md)
- [USAGE-004 — Workspace Usage Summary](./usage-004-workspace-usage-summary.md)

### Epic 9: Admin Dashboard

- [ADMIN-001 — View Workspace Documents Overview](./admin-001-view-workspace-documents-overview.md)
- [ADMIN-002 — View Ingestion Job Status](./admin-002-view-ingestion-job-status.md)
- [ADMIN-003 — View Recent Questions](./admin-003-view-recent-questions.md)
- [ADMIN-004 — View Usage Summary (Dashboard)](./admin-004-view-usage-summary-dashboard.md)
- [ADMIN-005 — View Failed Jobs Widget](./admin-005-view-failed-jobs-widget.md)

### Epic 10: Audit Logs and Security Events

- [AUDIT-001 — Document Upload Audit Event](./audit-001-document-upload-audit-event.md)
- [AUDIT-002 — Document Deletion Audit Event](./audit-002-document-deletion-audit-event.md)
- [AUDIT-003 — Re-index Audit Event](./audit-003-re-index-audit-event.md)
- [AUDIT-004 — User Role Change Audit Event](./audit-004-user-role-change-audit-event.md)
- [AUDIT-005 — Failed Authorization Audit Event](./audit-005-failed-authorization-audit-event.md)
- [AUDIT-006 — Agent Run Audit Event](./audit-006-agent-run-audit-event.md)
- [AUDIT-007 — View Audit Logs](./audit-007-view-audit-logs.md)

### Epic 11: Observability and Reliability

- [OBS-001 — Health Check Endpoint](./obs-001-health-check-endpoint.md)
- [OBS-002 — Structured Logging](./obs-002-structured-logging.md)
- [OBS-003 — Request ID Propagation](./obs-003-request-id-propagation.md)
- [OBS-004 — Standard API Error Format](./obs-004-standard-api-error-format.md)
- [OBS-005 — Ingestion Failure Handling](./obs-005-ingestion-failure-handling.md)
- [OBS-006 — Basic Metrics Endpoint](./obs-006-basic-metrics-endpoint.md)
- [OBS-007 — Background Worker Visibility](./obs-007-background-worker-visibility.md)

### Epic 12: Deployment and Developer Experience

- [INFRA-001 — Docker Compose Local Setup](./infra-001-docker-compose-local-setup.md)
- [INFRA-002 — Environment Variable Configuration](./infra-002-environment-variable-configuration.md)
- [INFRA-003 — Database Migrations](./infra-003-database-migrations.md)
- [INFRA-004 — Seed Demo Dataset](./infra-004-seed-demo-dataset.md)
- [INFRA-005 — GitHub Actions CI](./infra-005-github-actions-ci.md)
- [INFRA-006 — Terraform Deployment Scaffold](./infra-006-terraform-deployment-scaffold.md)
- [INFRA-007 — README and Architecture Documentation](./infra-007-readme-and-architecture-documentation.md)
- [INFRA-008 — OpenAPI API Documentation](./infra-008-openapi-api-documentation.md)

### Epic 13: Minimal Demo UI

- [UI-001 — Web App Scaffold and App Shell](./ui-001-web-app-scaffold-and-app-shell.md)
- [UI-002 — Login, Registration, and Session](./ui-002-login-registration-and-session.md)
- [UI-003 — Documents Page](./ui-003-documents-page.md)
- [UI-004 — RAG Question Page](./ui-004-rag-question-page.md)
- [UI-005 — Agent Investigation Page](./ui-005-agent-investigation-page.md)
- [UI-006 — Admin Dashboard Page](./ui-006-admin-dashboard-page.md)
