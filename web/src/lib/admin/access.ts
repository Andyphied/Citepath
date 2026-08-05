import { isAdminRole } from "@/lib/api/types";

/**
 * Owner/Admin may view the admin dashboard (WS-005 / VIEW_ADMIN_DASHBOARD).
 * Viewer and Member are denied (nav hidden + page access-denied state).
 */
export function canAccessAdminDashboard(
  role: string | undefined | null,
): boolean {
  return isAdminRole(role);
}
