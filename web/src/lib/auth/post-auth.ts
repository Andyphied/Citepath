import { sanitizeNextPath } from "@/lib/auth/safe-next";

/**
 * Resolve where to send the user after login/register.
 * Honors a sanitized `next` query; otherwise lands on home
 * (empty-workspace prompt lives there when memberships are empty).
 */
export function resolvePostAuthPath(
  next: string | null | undefined,
): string {
  return sanitizeNextPath(next);
}
