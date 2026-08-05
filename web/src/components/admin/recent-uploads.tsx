"use client";

import { DocumentStatusBadge } from "@/components/documents/status-badge";
import { formatJobTimestamp } from "@/lib/admin/format";
import type { RecentDocumentUpload } from "@/lib/api/types";

export function RecentUploadsList({
  uploads,
}: {
  uploads: RecentDocumentUpload[];
}) {
  if (uploads.length === 0) {
    return (
      <div className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-6 py-10 text-center">
        <p className="font-[family-name:var(--font-display)] text-xl text-[var(--ink)]">
          No recent uploads
        </p>
        <p className="mx-auto mt-2 max-w-md text-sm text-[var(--muted)] leading-relaxed">
          Documents uploaded to this workspace will show here newest first.
        </p>
      </div>
    );
  }

  return (
    <ul className="divide-y divide-[var(--border)] rounded-md border border-[var(--border)] bg-[var(--surface)]">
      {uploads.map((doc) => (
        <li
          key={doc.id}
          className="flex flex-wrap items-center justify-between gap-3 px-4 py-3"
        >
          <div className="min-w-0">
            <p className="truncate font-medium text-[var(--ink)]">
              {doc.title ?? "Untitled document"}
            </p>
            <p className="mt-0.5 text-xs text-[var(--muted)]">
              {formatJobTimestamp(doc.created_at)}
            </p>
          </div>
          <DocumentStatusBadge
            status={doc.status}
            label={doc.status_label}
          />
        </li>
      ))}
    </ul>
  );
}
