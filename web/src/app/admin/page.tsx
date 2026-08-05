"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { AdminSummaryCards } from "@/components/admin/summary-cards";
import { IngestionJobsTable } from "@/components/admin/ingestion-jobs-table";
import { RecentUploadsList } from "@/components/admin/recent-uploads";
import { AppShell } from "@/components/app-shell";
import { ErrorState } from "@/components/error-state";
import { LoadingState } from "@/components/loading-state";
import { useWorkspace } from "@/components/workspace-provider";
import { canAccessAdminDashboard } from "@/lib/admin/access";
import {
  isAdminDashboardDataCurrent,
  shouldApplyAdminResponse,
} from "@/lib/admin/status";
import {
  getDocumentsOverview,
  getFailedJobsWidget,
  getWorkspaceUsageSummary,
  listIngestionJobs,
} from "@/lib/api/admin";
import { ApiError } from "@/lib/api/client";
import type {
  AdminIngestionJobItem,
  DocumentStatusCounts,
  FailedJobsWidgetResponse,
  RecentDocumentUpload,
  UsageTotals,
} from "@/lib/api/types";

const JOBS_PAGE_SIZE = 20;

function errorMessage(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback;
}

export default function AdminPage() {
  const {
    activeWorkspace,
    activeWorkspaceId,
    loading: workspaceLoading,
    error: workspaceError,
    refresh: refreshWorkspaces,
  } = useWorkspace();

  const canAccess = canAccessAdminDashboard(activeWorkspace?.role);
  const activeWorkspaceIdRef = useRef(activeWorkspaceId);
  activeWorkspaceIdRef.current = activeWorkspaceId;
  /** Invalidates in-flight loads when workspace changes or a newer load starts. */
  const loadGenerationRef = useRef(0);

  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  /** Workspace id that current dashboard state was applied for (null = cleared). */
  const [dataWorkspaceId, setDataWorkspaceId] = useState<string | null>(null);
  const [byStatus, setByStatus] = useState<DocumentStatusCounts | null>(null);
  const [totalDocuments, setTotalDocuments] = useState(0);
  const [recentUploads, setRecentUploads] = useState<RecentDocumentUpload[]>(
    [],
  );
  const [usageTotals, setUsageTotals] = useState<UsageTotals | null>(null);
  const [failedJobs, setFailedJobs] =
    useState<FailedJobsWidgetResponse | null>(null);
  const [jobs, setJobs] = useState<AdminIngestionJobItem[]>([]);
  const [jobsTotal, setJobsTotal] = useState(0);
  const [pendingCount, setPendingCount] = useState(0);

  const clearDashboardState = useCallback(() => {
    setDataWorkspaceId(null);
    setByStatus(null);
    setTotalDocuments(0);
    setRecentUploads([]);
    setUsageTotals(null);
    setFailedJobs(null);
    setJobs([]);
    setJobsTotal(0);
    setPendingCount(0);
    setLoadError(null);
  }, []);

  // Mirror UI-005: drop prior workspace UI state immediately on switch.
  useEffect(() => {
    loadGenerationRef.current += 1;
    clearDashboardState();
    setLoading(false);
  }, [activeWorkspaceId, clearDashboardState]);

  const loadDashboard = useCallback(async () => {
    const requestWorkspaceId = activeWorkspaceId;
    if (!requestWorkspaceId || !canAccess) {
      clearDashboardState();
      setLoading(false);
      return;
    }

    const generation = ++loadGenerationRef.current;
    setLoading(true);
    setLoadError(null);
    try {
      const [overview, usage, failed, jobList] = await Promise.all([
        getDocumentsOverview(requestWorkspaceId),
        getWorkspaceUsageSummary(requestWorkspaceId),
        getFailedJobsWidget(requestWorkspaceId),
        listIngestionJobs(requestWorkspaceId, {
          page: 1,
          pageSize: JOBS_PAGE_SIZE,
        }),
      ]);

      if (
        generation !== loadGenerationRef.current ||
        !shouldApplyAdminResponse(
          requestWorkspaceId,
          activeWorkspaceIdRef.current,
        )
      ) {
        return;
      }

      setDataWorkspaceId(requestWorkspaceId);
      setByStatus(overview.by_status);
      setTotalDocuments(overview.total);
      setRecentUploads(overview.recent_uploads ?? []);
      setUsageTotals(usage.totals);
      setFailedJobs(failed);
      setJobs(jobList.items ?? []);
      setJobsTotal(jobList.total ?? 0);
      setPendingCount(jobList.pending_count ?? 0);
    } catch (err) {
      if (
        generation !== loadGenerationRef.current ||
        !shouldApplyAdminResponse(
          requestWorkspaceId,
          activeWorkspaceIdRef.current,
        )
      ) {
        return;
      }
      setDataWorkspaceId(requestWorkspaceId);
      setLoadError(errorMessage(err, "Failed to load admin dashboard."));
      setByStatus(null);
      setTotalDocuments(0);
      setRecentUploads([]);
      setUsageTotals(null);
      setFailedJobs(null);
      setJobs([]);
      setJobsTotal(0);
      setPendingCount(0);
    } finally {
      if (
        generation === loadGenerationRef.current &&
        shouldApplyAdminResponse(
          requestWorkspaceId,
          activeWorkspaceIdRef.current,
        )
      ) {
        setLoading(false);
      }
    }
  }, [activeWorkspaceId, canAccess, clearDashboardState]);

  useEffect(() => {
    if (workspaceLoading) {
      return;
    }
    void loadDashboard();
  }, [workspaceLoading, loadDashboard]);

  const dataCurrent = isAdminDashboardDataCurrent(
    dataWorkspaceId,
    activeWorkspaceId,
  );
  const showError =
    Boolean(activeWorkspaceId) && canAccess && dataCurrent && Boolean(loadError);
  const showLoading =
    Boolean(activeWorkspaceId) &&
    canAccess &&
    !workspaceLoading &&
    !showError &&
    (loading || !dataCurrent);
  const showDashboard =
    Boolean(activeWorkspaceId) &&
    canAccess &&
    dataCurrent &&
    !loading &&
    !loadError;

  return (
    <AppShell title="Admin">
      <section className="mx-auto flex w-full max-w-5xl flex-col gap-8">
        <div>
          <h2 className="font-[family-name:var(--font-display)] text-2xl text-[var(--ink)]">
            Admin dashboard
          </h2>
          <p className="mt-2 text-sm text-[var(--muted)] leading-relaxed">
            Corpus health, ingestion jobs, and 7-day usage for the active
            workspace.
          </p>
        </div>

        {workspaceLoading ? (
          <LoadingState label="Loading workspace…" />
        ) : null}

        {workspaceError ? (
          <ErrorState
            title="Workspace error"
            message={workspaceError}
            onRetry={() => {
              void refreshWorkspaces();
            }}
          />
        ) : null}

        {!workspaceLoading && !workspaceError && !activeWorkspaceId ? (
          <p className="text-sm text-[var(--muted)]">
            Select or create a workspace to view the admin dashboard.
          </p>
        ) : null}

        {activeWorkspaceId && !canAccess ? (
          <div
            className="rounded-md border border-[var(--danger-border)] bg-[var(--danger-bg)] px-4 py-4 text-sm text-[var(--danger)]"
            role="alert"
          >
            <p className="font-medium">Access denied</p>
            <p className="mt-1 text-[var(--danger)]/90">
              The admin dashboard is available to Owner and Admin roles only.
              Your role in this workspace is{" "}
              <span className="font-medium">
                {activeWorkspace?.role ?? "unknown"}
              </span>
              .
            </p>
          </div>
        ) : null}

        {showLoading ? <LoadingState label="Loading dashboard…" /> : null}

        {showError ? (
          <ErrorState
            title="Could not load dashboard"
            message={loadError ?? "Failed to load admin dashboard."}
            onRetry={() => {
              void loadDashboard();
            }}
          />
        ) : null}

        {showDashboard ? (
          <>
            <AdminSummaryCards
              byStatus={byStatus}
              totalDocuments={totalDocuments}
              usageTotals={usageTotals}
              failedJobs={failedJobs}
            />

            <section className="flex flex-col gap-3">
              <div>
                <h3 className="font-[family-name:var(--font-display)] text-lg text-[var(--ink)]">
                  Ingestion jobs
                </h3>
                <p className="mt-1 text-sm text-[var(--muted)]">
                  Document title, status, timing, and failure errors.
                </p>
              </div>
              <IngestionJobsTable
                jobs={jobs}
                total={jobsTotal}
                pendingCount={pendingCount}
              />
            </section>

            <section className="flex flex-col gap-3">
              <div>
                <h3 className="font-[family-name:var(--font-display)] text-lg text-[var(--ink)]">
                  Recent uploads
                </h3>
                <p className="mt-1 text-sm text-[var(--muted)]">
                  Newest documents in this workspace (from documents overview).
                </p>
              </div>
              <RecentUploadsList uploads={recentUploads} />
            </section>
          </>
        ) : null}
      </section>
    </AppShell>
  );
}
