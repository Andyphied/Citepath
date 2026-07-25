/**
 * Sanitize a post-login `next` query value to a same-app relative path.
 * Rejects open redirects (protocol-relative, absolute URLs, backslash tricks).
 */
export function sanitizeNextPath(raw: string | null | undefined): string {
  if (raw == null || raw === "") {
    return "/";
  }

  // Same-app relative paths only.
  if (!raw.startsWith("/")) {
    return "/";
  }

  // Protocol-relative (//evil.example) and scheme tricks.
  if (raw.startsWith("//") || raw.includes("://")) {
    return "/";
  }

  // Backslash tricks (/\evil, \\host, mixed separators).
  if (raw.includes("\\")) {
    return "/";
  }

  return raw;
}
