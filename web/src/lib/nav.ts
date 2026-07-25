export type NavItem = {
  href: string;
  label: string;
  /** When true, only owner/admin see this item as enabled. */
  adminOnly?: boolean;
};

export const PRIMARY_NAV: NavItem[] = [
  { href: "/documents", label: "Documents" },
  { href: "/ask", label: "Ask" },
  { href: "/agent", label: "Agent" },
  { href: "/admin", label: "Admin", adminOnly: true },
];

/** Public auth routes do not require a session cookie. */
export function isProtectedPath(pathname: string): boolean {
  if (pathname === "/login" || pathname.startsWith("/login/")) {
    return false;
  }
  if (pathname === "/register" || pathname.startsWith("/register/")) {
    return false;
  }
  return true;
}
