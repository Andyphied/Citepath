import { apiFetch } from "@/lib/api/client";
import type { WorkspaceListResponse } from "@/lib/api/types";

/** GET /workspaces — memberships for the authenticated user (WS-002 / WS-006). */
export function listWorkspaces(): Promise<WorkspaceListResponse> {
  return apiFetch<WorkspaceListResponse>("/workspaces");
}
