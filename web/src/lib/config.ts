/** Public runtime configuration for the AtlasOps web app. */

export function getApiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (!raw) {
    return "http://localhost:8000";
  }
  return raw.replace(/\/+$/, "");
}

export const AUTH_TOKEN_COOKIE = "atlasops_token";
export const ACTIVE_WORKSPACE_STORAGE_KEY = "atlasops_active_workspace_id";
