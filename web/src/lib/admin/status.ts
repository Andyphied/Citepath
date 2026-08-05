import type {
  AdminIngestionJobItem,
  IngestionJobStatusValue,
} from "@/lib/api/types";
import type { StatusBadgeTone } from "@/lib/documents/status";

const JOB_STATUS_TONES: Record<string, StatusBadgeTone> = {
  pending: "gray",
  processing: "yellow",
  completed: "green",
  failed: "red",
};

const TONE_CLASSES: Record<StatusBadgeTone, string> = {
  gray: "bg-slate-100 text-slate-700 border-slate-200",
  yellow: "bg-amber-50 text-amber-800 border-amber-200",
  green: "bg-emerald-50 text-emerald-800 border-emerald-200",
  red: "bg-rose-50 text-rose-800 border-rose-200",
};

export function ingestionJobStatusTone(
  status: IngestionJobStatusValue,
): StatusBadgeTone {
  return JOB_STATUS_TONES[status] ?? "gray";
}

export function ingestionJobStatusBadgeClass(
  status: IngestionJobStatusValue,
): string {
  return TONE_CLASSES[ingestionJobStatusTone(status)];
}

/** Discard stale dashboard payloads after a workspace switch mid-flight. */
export function shouldApplyAdminResponse(
  requestWorkspaceId: string,
  activeWorkspaceId: string | null | undefined,
): boolean {
  return Boolean(activeWorkspaceId) && requestWorkspaceId === activeWorkspaceId;
}

/**
 * True when applied dashboard state belongs to the active workspace.
 * Prevents one-frame cross-workspace flashes before clear/load effects run.
 */
export function isAdminDashboardDataCurrent(
  dataWorkspaceId: string | null,
  activeWorkspaceId: string | null | undefined,
): boolean {
  return Boolean(activeWorkspaceId) && dataWorkspaceId === activeWorkspaceId;
}

/** Display text for a failed ingestion job (ADMIN-005 / UI-006 AC). */
export function failedJobErrorText(job: AdminIngestionJobItem): string {
  const message = job.error_message?.trim();
  return message || "Ingestion failed.";
}
