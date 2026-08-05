"use client";

import {
  formatCostUsd,
  formatTokenCount,
} from "@/lib/admin/format";
import { failedJobErrorText } from "@/lib/admin/status";
import type {
  DocumentStatusCounts,
  FailedJobsWidgetResponse,
  UsageTotals,
} from "@/lib/api/types";

function Card({
  title,
  children,
  highlight,
}: {
  title: string;
  children: React.ReactNode;
  highlight?: boolean;
}) {
  return (
    <div
      className={`rounded-md border px-4 py-4 ${
        highlight
          ? "border-[var(--danger-border)] bg-[var(--danger-bg)]"
          : "border-[var(--border)] bg-[var(--surface)]"
      }`}
    >
      <p className="text-xs uppercase tracking-wide text-[var(--muted)]">
        {title}
      </p>
      <div className="mt-2">{children}</div>
    </div>
  );
}

export function AdminSummaryCards({
  byStatus,
  totalDocuments,
  usageTotals,
  failedJobs,
}: {
  byStatus: DocumentStatusCounts | null;
  totalDocuments: number;
  usageTotals: UsageTotals | null;
  failedJobs: FailedJobsWidgetResponse | null;
}) {
  const status = byStatus ?? {
    uploaded: 0,
    processing: 0,
    indexed: 0,
    failed: 0,
  };
  const failed7d = failedJobs?.failed_last_7d ?? 0;
  const failed24h = failedJobs?.failed_last_24h ?? 0;
  const failedItems = failedJobs?.items ?? [];
  const prompt = usageTotals?.prompt_tokens ?? 0;
  const completion = usageTotals?.completion_tokens ?? 0;
  const embedding = usageTotals?.embedding_tokens ?? 0;
  const calls = usageTotals?.call_count ?? 0;
  const cost = usageTotals?.estimated_cost_usd ?? 0;

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <Card title="Documents by status">
        <p className="font-[family-name:var(--font-display)] text-2xl text-[var(--ink)]">
          {totalDocuments}
          <span className="ml-2 text-sm font-normal text-[var(--muted)]">
            total
          </span>
        </p>
        <ul className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1 text-sm text-[var(--muted)]">
          <li>
            Indexed{" "}
            <span className="font-medium text-[var(--ink)]">
              {status.indexed}
            </span>
          </li>
          <li>
            Processing{" "}
            <span className="font-medium text-[var(--ink)]">
              {status.processing}
            </span>
          </li>
          <li>
            Uploaded{" "}
            <span className="font-medium text-[var(--ink)]">
              {status.uploaded}
            </span>
          </li>
          <li>
            Failed{" "}
            <span className="font-medium text-[var(--ink)]">
              {status.failed}
            </span>
          </li>
        </ul>
      </Card>

      <Card title="Usage · last 7 days">
        <p className="font-[family-name:var(--font-display)] text-2xl text-[var(--ink)]">
          {formatCostUsd(cost)}
        </p>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Estimated cost · {formatTokenCount(calls)} calls
        </p>
        <ul className="mt-3 space-y-1 text-sm text-[var(--muted)]">
          <li>
            Prompt{" "}
            <span className="font-medium text-[var(--ink)]">
              {formatTokenCount(prompt)}
            </span>
          </li>
          <li>
            Completion{" "}
            <span className="font-medium text-[var(--ink)]">
              {formatTokenCount(completion)}
            </span>
          </li>
          <li>
            Embedding{" "}
            <span className="font-medium text-[var(--ink)]">
              {formatTokenCount(embedding)}
            </span>
          </li>
        </ul>
      </Card>

      <Card title="Failed jobs" highlight={failed7d > 0}>
        <p
          className={`font-[family-name:var(--font-display)] text-2xl ${
            failed7d > 0 ? "text-[var(--danger)]" : "text-[var(--ink)]"
          }`}
        >
          {failed7d}
        </p>
        <p className="mt-1 text-sm text-[var(--muted)]">
          {failed7d === 0
            ? (failedJobs?.empty_message ?? "No failed jobs.")
            : `${failed24h} in last 24h · ${failed7d} in last 7 days`}
        </p>
        {failedItems.length > 0 ? (
          <ul className="mt-3 space-y-2 border-t border-[var(--danger-border)]/40 pt-3">
            {failedItems.map((job) => (
              <li key={job.id} className="text-sm">
                <p className="font-medium text-[var(--ink)]">
                  {job.document_title ?? "Untitled document"}
                </p>
                <p className="mt-0.5 text-[var(--danger)] leading-snug">
                  {failedJobErrorText(job)}
                </p>
              </li>
            ))}
          </ul>
        ) : null}
      </Card>
    </div>
  );
}
