# USAGE-BATCH-001 Implementation Note

Batch: **USAGE-003** (Cost Estimation) + **USAGE-004** (Workspace Usage Summary)

## Summary

Verified and tightened LLM/embedding cost estimation (`estimated_cost_usd` via static
price table), documented that estimates are not invoices, and shipped the first
`/admin/*` API: workspace usage summary with 7-day default window, Owner/Admin RBAC,
and aggregates from `usage_events`.

## Files Changed

| File | Purpose |
|------|---------|
| `app/modules/usage/cost_calculator.py` | Document assumptions; quantize to 6 decimal places |
| `app/modules/usage/exceptions.py` | `InvalidUsageRangeError` |
| `app/modules/usage/schemas.py` | Admin usage summary response models |
| `app/modules/usage/repository.py` | `aggregate_workspace_usage` (totals, by_day, by_operation) |
| `app/modules/usage/service.py` | `get_workspace_summary` (default last 7 days) |
| `app/api/routes/admin.py` | `GET /workspaces/{workspace_id}/admin/usage` |
| `app/api/deps.py` | `RequireViewAdminDashboardDep`, `UsageServiceDep` |
| `app/api/usage_errors.py` | 422 handler for invalid range |
| `app/main.py` | Mount admin router + exception handler |
| `README.md` | Cost estimate ≠ invoice documentation |
| `docs/06-api-design.md` | Align admin usage response shape |
| `docs/adr/ADR-007-token-usage-and-cost-tracking.md` | Note blended rates / README |
| `tests/unit/test_cost_calculator.py` | LLM + quantization coverage |
| `tests/unit/test_usage_summary_service.py` | Summary service unit tests |
| `tests/unit/test_usage_repository.py` | Aggregate query unit test |
| `tests/api/test_admin_usage.py` | Aggregation + RBAC + isolation API tests |

## Behavior Added

### USAGE-003

- Existing `UsageService.log_event` continues to populate `estimated_cost_usd` from
  `PRICING_USD_PER_1K_TOKENS` for known provider/model pairs.
- Costs quantized to 6 decimal places (`ROUND_HALF_UP`).
- Unknown models leave cost `NULL` (not invent a rate).
- Root README documents assumptions: estimates are demo/portfolio figures, not billing.

### USAGE-004

- `UsageService.get_workspace_summary(workspace_id, start?, end?)`
- `GET /workspaces/{workspace_id}/admin/usage?from=&to=`
- Default window: last 7 days ending now (UTC); bounds are `[from, to)`.
- Totals: `prompt_tokens`, `completion_tokens`, `embedding_tokens`,
  `estimated_cost_usd`, `call_count`
- Optional P1 breakdowns: `by_day`, `by_operation`
- RBAC: `PermissionAction.VIEW_ADMIN_DASHBOARD` (Owner/Admin); Viewer/Member → 403
- Invalid inverted range → `422 invalid_usage_range`
- Workspace isolation: aggregates always filter `usage_events.workspace_id`

## Tests Added

**Unit**

- Cost calculator: embedding, LLM completion, unknown model/provider, quantization
- Usage service: default 7-day window, inverted range error
- Repository: aggregate query wiring

**API** (Docker/testcontainers)

- Owner: 10+ events today → totals match (excludes events older than 7 days)
- Admin OK; Viewer 403; Member 403
- Cross-workspace isolation
- Invalid `from`/`to` → 422

## Decisions Made

- Kept static in-code price table per ADR-007 (not env/config table for MVP).
- Blended per-model USD/1K rate (no separate input/output pricing).
- Permission enforced at FastAPI dependency layer; `UsageService` stays free of
  workspace/RBAC dependencies (module boundary).
- `by_operation` returned as a list of objects (clearer than opaque map) while
  matching the fields in `docs/06-api-design.md`.

## Known Limitations

- Estimates are approximate; not invoice-grade (by design).
- No UI (ADMIN-004) — API only.
- No Prometheus metrics wiring here (OBS-006).
- Failed usage rows with `estimated_cost_usd=NULL` contribute `0` to cost sums.

## Follow-up Items

- **ADMIN-004:** Dashboard widget consuming this endpoint
- **OBS-006:** Metrics derived from the same calculator
- Optional: env overrides for rates if product later requires non-code updates
