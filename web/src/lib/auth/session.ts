import { AUTH_TOKEN_COOKIE } from "@/lib/config";

const TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24;

function canUseDom(): boolean {
  return typeof document !== "undefined";
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

export function setAccessToken(token: string): void {
  if (!canUseDom()) {
    return;
  }
  const encoded = encodeURIComponent(token);
  document.cookie = `${AUTH_TOKEN_COOKIE}=${encoded}; Path=/; Max-Age=${TOKEN_MAX_AGE_SECONDS}; SameSite=Lax`;
}

export function clearAccessToken(): void {
  if (!canUseDom()) {
    return;
  }
  document.cookie = `${AUTH_TOKEN_COOKIE}=; Path=/; Max-Age=0; SameSite=Lax`;
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
