/** Public runtime configuration for the Citepath web app. */

export function getApiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (!raw) {
    return "http://localhost:8000";
  }
  return raw.replace(/\/+$/, "");
}

export const AUTH_TOKEN_COOKIE = "citepath_token";
export const ACTIVE_WORKSPACE_STORAGE_KEY = "citepath_active_workspace_id";
