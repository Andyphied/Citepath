import { AUTH_TOKEN_COOKIE } from "@/lib/config";

const TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24;

function canUseDom(): boolean {
  return typeof document !== "undefined";
}

function cookieSecureFlag(): string {
  if (!canUseDom()) {
    return "";
  }
  return window.location.protocol === "https:" ? "; Secure" : "";
}

export function getAccessToken(): string | null {
  if (!canUseDom()) {
    return null;
  }
  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${AUTH_TOKEN_COOKIE}=`));
  if (!match) {
    return null;
  }
  const value = match.slice(AUTH_TOKEN_COOKIE.length + 1);
  return value ? decodeURIComponent(value) : null;
}

/**
 * Persist JWT in a JS-readable cookie so:
 * - Next.js middleware can gate protected routes
 * - `apiFetch` can inject `Authorization: Bearer …`
 *
 * HttpOnly Set-Cookie from the API would break the existing Bearer client
 * pattern without cookie-auth support on FastAPI; documented in UI-002 note.
 */
export function setAccessToken(token: string): void {
  if (!canUseDom()) {
    return;
  }
  const encoded = encodeURIComponent(token);
  document.cookie = `${AUTH_TOKEN_COOKIE}=${encoded}; Path=/; Max-Age=${TOKEN_MAX_AGE_SECONDS}; SameSite=Lax${cookieSecureFlag()}`;
}

export function clearAccessToken(): void {
  if (!canUseDom()) {
    return;
  }
  document.cookie = `${AUTH_TOKEN_COOKIE}=; Path=/; Max-Age=0; SameSite=Lax${cookieSecureFlag()}`;
}

export function isAuthenticated(): boolean {
  return Boolean(getAccessToken());
}

/** Cookie presence check for Next.js middleware (Edge runtime). */
export function hasAuthCookie(
  cookieHeader: string | null | undefined,
): boolean {
  if (!cookieHeader) {
    return false;
  }
  return cookieHeader
    .split(";")
    .map((part) => part.trim())
    .some((part) => {
      if (!part.startsWith(`${AUTH_TOKEN_COOKIE}=`)) {
        return false;
      }
      const value = part.slice(AUTH_TOKEN_COOKIE.length + 1);
      return value.length > 0;
    });
}
