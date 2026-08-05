import { apiFetch } from "@/lib/api/client";
import type {
  AdminIngestionJobListResponse,
  DocumentsOverviewResponse,
  FailedJobsWidgetResponse,
  WorkspaceUsageSummaryResponse,
} from "@/lib/api/types";

/** GET /workspaces/{id}/admin/documents-overview (ADMIN-001). */
export function getDocumentsOverview(
  workspaceId: string,
): Promise<DocumentsOverviewResponse> {
  return apiFetch<DocumentsOverviewResponse>(
    `/workspaces/${workspaceId}/admin/documents-overview`,
  );
}

export type ListIngestionJobsParams = {
  page?: number;
  pageSize?: number;
  status?: string;
};

/** GET /workspaces/{id}/admin/ingestion-jobs (ADMIN-002). */
export function listIngestionJobs(
  workspaceId: string,
  params: ListIngestionJobsParams = {},
): Promise<AdminIngestionJobListResponse> {
  const query = new URLSearchParams();
  if (params.page != null) {
    query.set("page", String(params.page));
  }
  if (params.pageSize != null) {
    query.set("page_size", String(params.pageSize));
  }
  if (params.status) {
    query.set("status", params.status);
  }
  const qs = query.toString();
  const path = `/workspaces/${workspaceId}/admin/ingestion-jobs${qs ? `?${qs}` : ""}`;
  return apiFetch<AdminIngestionJobListResponse>(path);
}

/** GET /workspaces/{id}/admin/failed-jobs (ADMIN-005). */
export function getFailedJobsWidget(
  workspaceId: string,
): Promise<FailedJobsWidgetResponse> {
  return apiFetch<FailedJobsWidgetResponse>(
    `/workspaces/${workspaceId}/admin/failed-jobs`,
  );
}

export type GetWorkspaceUsageParams = {
  from?: string;
  to?: string;
};

/** GET /workspaces/{id}/admin/usage (USAGE-004 / ADMIN-004). Default window: last 7 days. */
export function getWorkspaceUsageSummary(
  workspaceId: string,
  params: GetWorkspaceUsageParams = {},
): Promise<WorkspaceUsageSummaryResponse> {
  const query = new URLSearchParams();
  if (params.from) {
    query.set("from", params.from);
  }
  if (params.to) {
    query.set("to", params.to);
  }
  const qs = query.toString();
  const path = `/workspaces/${workspaceId}/admin/usage${qs ? `?${qs}` : ""}`;
  return apiFetch<WorkspaceUsageSummaryResponse>(path);
}
