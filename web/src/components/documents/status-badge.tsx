"use client";

import { documentStatusBadgeClass } from "@/lib/documents/status";
import type { DocumentStatusValue } from "@/lib/api/types";

export function DocumentStatusBadge({
  status,
  label,
}: {
  status: DocumentStatusValue;
  label: string;
}) {
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium ${documentStatusBadgeClass(status)}`}
    >
      {label}
    </span>
  );
}
