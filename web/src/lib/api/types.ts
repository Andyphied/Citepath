/** Shared API response types aligned with AtlasOps backend schemas. */

export type WorkspaceRole = "owner" | "admin" | "member" | "viewer";

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

export interface User {
  id: string;
  email: string;
  name: string | null;
  created_at: string;
}

export interface WorkspaceListItem {
  id: string;
  name: string;
  role: WorkspaceRole | string;
  created_at: string;
}

export interface WorkspaceListResponse {
  items: WorkspaceListItem[];
}

export function isAdminRole(role: string | undefined | null): boolean {
  return role === "owner" || role === "admin";
}
