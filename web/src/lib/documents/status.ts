import type { DocumentStatusValue } from "@/lib/api/types";

export type StatusBadgeTone = "gray" | "yellow" | "green" | "red";

const STATUS_TONES: Record<string, StatusBadgeTone> = {
  uploaded: "gray",
  processing: "yellow",
  indexed: "green",
  failed: "red",
};

const TONE_CLASSES: Record<StatusBadgeTone, string> = {
  gray: "bg-slate-100 text-slate-700 border-slate-200",
  yellow: "bg-amber-50 text-amber-800 border-amber-200",
  green: "bg-emerald-50 text-emerald-800 border-emerald-200",
  red: "bg-rose-50 text-rose-800 border-rose-200",
};

/** Map API status → demo-friendly badge tone (UI-003 notes). */
export function documentStatusTone(
  status: DocumentStatusValue,
): StatusBadgeTone {
  return STATUS_TONES[status] ?? "gray";
}

export function documentStatusBadgeClass(
  status: DocumentStatusValue,
): string {
  return TONE_CLASSES[documentStatusTone(status)];
}

/** In-flight statuses that should trigger list polling. */
export function isDocumentInFlight(status: DocumentStatusValue): boolean {
  return status === "uploaded" || status === "processing";
}

export function anyDocumentInFlight(
  items: ReadonlyArray<{ status: DocumentStatusValue }>,
): boolean {
  return items.some((item) => isDocumentInFlight(item.status));
}
