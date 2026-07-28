"use client";

import { DocumentStatusBadge } from "@/components/documents/status-badge";
import type { DocumentItem } from "@/lib/api/types";
import {
  formatFileType,
  formatUploadedAt,
  formatUploaderId,
} from "@/lib/documents/format";
import { anyDocumentInFlight } from "@/lib/documents/status";

export function DocumentsTable({
  documents,
  total,
  currentUserId,
}: {
  documents: DocumentItem[];
  total: number;
  currentUserId?: string | null;
}) {
  return (
    <div className="overflow-x-auto rounded-md border border-[var(--border)] bg-[var(--surface)]">
      <table className="min-w-full text-left text-sm">
        <caption className="sr-only">Workspace documents ({total})</caption>
        <thead className="border-b border-[var(--border)] bg-[var(--canvas)] text-xs uppercase tracking-wide text-[var(--muted)]">
          <tr>
            <th className="px-4 py-3 font-medium">Title</th>
            <th className="px-4 py-3 font-medium">Type</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Uploaded</th>
            <th className="px-4 py-3 font-medium">Uploader</th>
          </tr>
        </thead>
        <tbody>
          {documents.map((doc) => (
            <tr
              key={doc.id}
              className="border-b border-[var(--border)] last:border-b-0"
            >
              <td className="px-4 py-3 font-medium text-[var(--ink)]">
                {doc.title}
              </td>
              <td className="px-4 py-3 font-[family-name:var(--font-mono)] text-xs text-[var(--muted)]">
                {formatFileType(doc.file_type)}
              </td>
              <td className="px-4 py-3">
                <DocumentStatusBadge
                  status={doc.status}
                  label={doc.status_label}
                />
              </td>
              <td className="px-4 py-3 text-[var(--muted)]">
                {formatUploadedAt(doc.created_at)}
              </td>
              <td className="px-4 py-3 font-[family-name:var(--font-mono)] text-xs text-[var(--muted)]">
                {formatUploaderId(doc.uploaded_by, currentUserId)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {anyDocumentInFlight(documents) ? (
        <p className="border-t border-[var(--border)] px-4 py-2 text-xs text-[var(--muted)]">
          Refreshing while documents are processing…
        </p>
      ) : null}
    </div>
  );
}
