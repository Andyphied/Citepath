# ADMIN-BATCH-002 Implementation Note

Batch: **ADMIN-001** + **ADMIN-002** + **ADMIN-003** + **ADMIN-004** (verify) + **ADMIN-005**

## Summary

Shipped Owner/Admin-only admin dashboard aggregate APIs for documents overview,
ingestion jobs, recent questions, and failed-jobs widget. Confirmed **ADMIN-004**
is satisfied by existing **USAGE-004** `GET .../admin/usage` (no duplicate endpoint).

## Files Changed

| File | Purpose |
|------|---------|
| `app/modules/admin/__init__.py` | Admin module package |
| `app/modules/admin/schemas.py` | Response models for dashboard aggregates |
| `app/modules/admin/service.py` | `AdminService` orchestration (read-only) |
| `app/modules/documents/repository.py` | `count_by_status_for_workspace` |
| `app/modules/ingestion/job_repository.py` | Paginated list + title join; `count_failed_since` |
| `app/modules/rag/repository.py` | `list_recent_user_questions_paginated` |
| `app/api/deps.py` | `AdminServiceDep` |
| `app/api/routes/admin.py` | New admin routes |
| `docs/06-api-design.md` | Document new admin endpoints |
| `docs/04-module-boundaries.md` | Admin module exposes list |
| `README.md` | Mention admin aggregate paths |
| `tests/unit/test_admin_service.py` | Unit coverage for overview/widget helpers |
| `tests/api/test_admin_dashboard.py` | API + RBAC + isolation tests |

## Behavior Added

### ADMIN-001 — Documents overview

- `GET /workspaces/{workspace_id}/admin/documents-overview`
- Returns `total`, `by_status` (`uploaded`/`processing`/`indexed`/`failed`), and
  `recent_uploads` (newest first, limit 10)
- RBAC: `VIEW_ADMIN_DASHBOARD` (Owner/Admin)

### ADMIN-002 — Ingestion jobs

- `GET /workspaces/{workspace_id}/admin/ingestion-jobs?status=&page=&page_size=`
- Joins document title; includes `error_message`, `attempt_count`
- Failed filter: `?status=failed`

### ADMIN-003 — Recent questions

- `GET /workspaces/{workspace_id}/admin/recent-questions`
- Default `page_size=50` (max 100)
- User-role messages only (assistant/system excluded)
- Fields: user id/name/email, timestamp, truncated `question_preview` (200 chars)

### ADMIN-004 — Usage summary (verified, not duplicated)

- **Existing:** `GET /workspaces/{workspace_id}/admin/usage` (USAGE-004)
- Default last 7 days; totals include `estimated_cost_usd` and token counts
- Owner/Admin via `RequireViewAdminDashboardDep`
- Dashboard UI (UI-006) should call this endpoint; no second usage API added
- Covered by `tests/api/test_admin_usage.py` from USAGE-BATCH-001

### ADMIN-005 — Failed jobs widget

- `GET /workspaces/{workspace_id}/admin/failed-jobs`
- Returns `failed_last_24h`, `failed_last_7d`, recent failed `items`, and
  `empty_message: "No failed jobs."` when 7d count is 0
- Clients link to full list via `.../admin/ingestion-jobs?status=failed`

## Tests Added

**Unit**

- Question preview truncation
- Documents overview count mapping
- Failed widget empty state
- Ingestion job list includes document title / error

**API** (Docker/testcontainers)

- Documents overview counts + recent order
- Failed ingestion job surfaces with title + error_message
- Three recent questions appear with timestamps (assistant content excluded)
- Failed widget: empty state + 24h/7d counts
- Viewer/Member → 403 on all new endpoints
- Admin role → 200
- Cross-workspace isolation

## Decisions Made

- Introduced `app/modules/admin` aggregation service per module-boundary docs;
  reuses document / ingestion / RAG repositories (no ORM owned by admin).
- ADMIN-004 reuses USAGE-004 endpoint rather than inventing a dashboard-specific
  usage route (matches story notes).
- Failed-jobs widget endpoint returns counts + sample items; full filtered list
  remains ADMIN-002 with `status=failed`.
- Question preview truncates at 200 characters; full assistant prompts never returned.

## Known Limitations

- No frontend (UI-006 out of scope).
- No retry of failed jobs (ING-007 out of scope).
- No Prometheus metrics (OBS-006 out of scope).
- Failed-job time windows use `ingestion_jobs.created_at` (not `completed_at`).
- Recent questions include all user messages in the workspace (RAG + agent modes)
  that are role=`user`; product may later filter `mode=rag` only.

## Follow-up Items

- **UI-006:** Wire dashboard widgets to these endpoints + `/admin/usage` (completed)
- **ING-007:** Retry failed ingestion jobs from admin list
- Optional: filter recent-questions by `Conversation.mode == rag`
