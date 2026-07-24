# AUDIT-BATCH-001 Implementation Note

Batch: **AUDIT-001** (document upload) + **AUDIT-004** (role change) + **AUDIT-007** (view audit logs), with verification of **AUDIT-002** / **AUDIT-003** / **AUDIT-005** emitters.

## Summary

Completed missing audit emitters for document upload and member role changes, hardened `AuditRepository.create` to commit (so 403 denials persist), and shipped `GET /workspaces/{workspace_id}/admin/audit-logs` for Owner/Admin with filters and pagination. Existing delete, re-index, and failed-authorization emitters were verified and gap-tested.

## Files Changed

| File | Purpose |
|------|---------|
| `app/modules/audit/repository.py` | `create` commits; `list_for_workspace` with filters/pagination |
| `app/modules/audit/service.py` | Admin list query + date-range validation |
| `app/modules/audit/schemas.py` | `AuditLogResponse` / `AuditLogListResponse` |
| `app/modules/audit/exceptions.py` | `InvalidAuditRangeError` |
| `app/modules/documents/service.py` | Emit `document.uploaded` on successful upload |
| `app/modules/workspaces/service.py` | Emit `member.role_changed` on role update |
| `app/api/routes/admin.py` | `GET .../admin/audit-logs` |
| `app/api/deps.py` | `AuditServiceDep`; inject audit repo into `WorkspaceService` |
| `app/api/audit_errors.py` | 422 handler for invalid audit date range |
| `app/main.py` | Register audit range exception handler |
| `docs/04-module-boundaries.md` | Event catalog update |
| `docs/06-api-design.md` | Audit-logs query contract |
| `docs/09-security-and-rbac.md` | Align event type names with code |
| `tests/unit/test_audit_service.py` | List filters + inverted range |
| `tests/unit/test_document_service.py` | Upload audit assertion |
| `tests/unit/test_workspace_service.py` | Role-change audit assertion |
| `tests/api/test_admin_audit_logs.py` | RBAC, isolation, filters, pagination |
| `tests/api/test_documents_upload.py` | Persist `document.uploaded` |
| `tests/api/test_workspaces_member_management.py` | Persist `member.role_changed` |
| `tests/api/test_documents_delete.py` | Viewer delete → `failed_authorization` |

## Behavior Added

### Event type naming (source of truth: code)

| Story event (backlog) | Implemented `event_type` | Notes |
|-----------------------|--------------------------|-------|
| `document.uploaded` | `document.uploaded` | AUDIT-001 |
| `document.deleted` | `document.deleted` | AUDIT-002 (pre-existing) |
| `document.reindex_requested` | `document.reindex_requested` | AUDIT-003 (pre-existing) |
| `member.role_changed` | `member.role_changed` | AUDIT-004 |
| `authz.denied` | `failed_authorization` | AUDIT-005 — keep existing WS-005 name |
| `agent.run_completed` | `agent.run_completed` | AUDIT-006 (prior batch) |

### AUDIT-001

- On successful upload, emit `document.uploaded` with metadata `{document_id, title}` only (no file content).
- Actor = uploader; workspace scoped.

### AUDIT-004

- On successful role change when `old_role != new_role`, emit `member.role_changed` with `{target_user_id, old_role, new_role}`.
- Actor = caller performing the PATCH.

### AUDIT-007

- `GET /workspaces/{workspace_id}/admin/audit-logs`
- Query: `event_type`, `actor_user_id`, `from`, `to` (`[from, to)`), `page`, `page_size` (max 100)
- Response: `{ items, total, page, page_size }` newest-first
- RBAC: `VIEW_ADMIN_DASHBOARD` (Owner/Admin); Viewer/Member → 403
- Workspace isolation via `workspace_id` filter
- No delete/update API (append-only)

### AUDIT-002 / 003 / 005 verification

- **002:** `DocumentService.delete` already emits `document.deleted`; API test covered.
- **003:** `DocumentService.reindex` already emits `document.reindex_requested`; API test covered.
- **005:** `PermissionService` emits `failed_authorization`; invite Viewer/non-member tests existed; added Viewer document-delete 403 audit assertion.
- **Hardening:** `AuditRepository.create` now **commits** so denial audits persist even when the request ends in 403 (previously flush-only risked rollback on session close).

## Tests Added

**Unit**

- Upload audits `document.uploaded`
- Role change audits `member.role_changed` with old/new roles
- AuditService filter wiring + inverted range

**API** (Docker/testcontainers)

- Upload → audit row without content fields
- Owner role change Member→Viewer → audit metadata
- Admin list reverse chronological order
- Filters: event_type + actor + date window
- Pagination
- Viewer/Member 403
- Cross-workspace isolation
- Invalid `from`/`to` → 422 `invalid_audit_range`
- Viewer delete → `failed_authorization`

## Decisions Made

- Kept `failed_authorization` (not `authz.denied`) for compatibility with WS-005 and existing tests.
- Dotted event names for document/member/agent events (`document.uploaded`, `member.role_changed`).
- `AuditRepository.create` commits immediately so authz denials and emitters that do not share a later commit remain durable.
- Admin list lives in `AuditService` (audit module owns reads); thin admin route mirrors usage summary pattern.
- Optional `actor_user_id` filter added beyond the API design draft (story requires actor filter).

## Known Limitations

- No audit write rate-limiting for repeated authz spam (noted on AUDIT-005).
- IP address often null on mutate routes that do not yet thread `Request` client IP into services.
- No delete/export API for audit logs (by design).
- Admin dashboard UI widgets out of scope.

## Follow-up Items

- Gate 6: mark AUDIT-001/004/007 (and verified 002/003/005) `completed` after review + commit.
- Optionally propagate `ip_address` from document upload / member PATCH routes.
- AUDIT-005 rate-limit hardening if abuse becomes a concern.
