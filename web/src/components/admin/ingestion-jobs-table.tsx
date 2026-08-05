"use client";

import {
  formatJobTimestamp,
  jobStatusLabel,
} from "@/lib/admin/format";
import {
  failedJobErrorText,
  ingestionJobStatusBadgeClass,
} from "@/lib/admin/status";
import type { AdminIngestionJobItem } from "@/lib/api/types";

export function IngestionJobsTable({
  jobs,
  total,
  pendingCount,
}: {
  jobs: AdminIngestionJobItem[];
  total: number;
  pendingCount: number;
}) {
  if (jobs.length === 0) {
    return (
      <div className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-6 py-10 text-center">
        <p className="font-[family-name:var(--font-display)] text-xl text-[var(--ink)]">
          No ingestion jobs yet
        </p>
        <p className="mx-auto mt-2 max-w-md text-sm text-[var(--muted)] leading-relaxed">
          Upload a document to start the ingest loop. Jobs will appear here with
          status and timing.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-md border border-[var(--border)] bg-[var(--surface)]">
      <table className="min-w-full text-left text-sm">
        <caption className="sr-only">
          Ingestion jobs ({total}; {pendingCount} pending)
        </caption>
        <thead className="border-b border-[var(--border)] bg-[var(--canvas)] text-xs uppercase tracking-wide text-[var(--muted)]">
          <tr>
            <th className="px-4 py-3 font-medium">Document</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Started</th>
            <th className="px-4 py-3 font-medium">Completed</th>
            <th className="px-4 py-3 font-medium">Error</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => {
            const failed = job.status === "failed";
            return (
              <tr
                key={job.id}
                className={`border-b border-[var(--border)] last:border-b-0 ${
                  failed ? "bg-[var(--danger-bg)]/40" : ""
                }`}
              >
                <td className="px-4 py-3 font-medium text-[var(--ink)]">
                  {job.document_title ?? "Untitled document"}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium ${ingestionJobStatusBadgeClass(job.status)}`}
                  >
                    {jobStatusLabel(job.status)}
                  </span>
                </td>
                <td className="px-4 py-3 text-[var(--muted)]">
                  {formatJobTimestamp(job.started_at)}
                </td>
                <td className="px-4 py-3 text-[var(--muted)]">
                  {formatJobTimestamp(job.completed_at)}
                </td>
                <td
                  className={`px-4 py-3 text-sm ${
                    failed
                      ? "text-[var(--danger)]"
                      : "text-[var(--muted)]"
                  }`}
                >
                  {failed ? failedJobErrorText(job) : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="border-t border-[var(--border)] px-4 py-2 text-xs text-[var(--muted)]">
        Showing {jobs.length} of {total}
        {pendingCount > 0 ? ` · ${pendingCount} pending` : ""}
      </p>
    </div>
  );
}
