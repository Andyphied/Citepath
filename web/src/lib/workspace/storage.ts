import { ACTIVE_WORKSPACE_STORAGE_KEY } from "@/lib/config";

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof localStorage !== "undefined";
}

export function getStoredActiveWorkspaceId(): string | null {
  if (!canUseStorage()) {
    return null;
  }
  const value = localStorage.getItem(ACTIVE_WORKSPACE_STORAGE_KEY);
  return value && value.trim() ? value : null;
}

export function setStoredActiveWorkspaceId(workspaceId: string): void {
  if (!canUseStorage()) {
    return;
  }
  localStorage.setItem(ACTIVE_WORKSPACE_STORAGE_KEY, workspaceId);
}

export function clearStoredActiveWorkspaceId(): void {
  if (!canUseStorage()) {
    return;
  }
  localStorage.removeItem(ACTIVE_WORKSPACE_STORAGE_KEY);
}

/**
 * Resolve which workspace should be active given membership list + stored preference.
 * Prefers a still-valid stored id; otherwise the first membership.
 */
export function resolveActiveWorkspaceId(
  workspaceIds: string[],
  storedId: string | null,
): string | null {
  if (workspaceIds.length === 0) {
    return null;
  }
  if (storedId && workspaceIds.includes(storedId)) {
    return storedId;
  }
  return workspaceIds[0] ?? null;
}

/** Build a workspace-scoped API path for subsequent calls (WS-006 pattern). */
export function workspaceApiPath(
  workspaceId: string,
  suffix = "",
): string {
  const trimmed = suffix.replace(/^\/+/, "");
  if (!trimmed) {
    return `/workspaces/${workspaceId}`;
  }
  return `/workspaces/${workspaceId}/${trimmed}`;
}
