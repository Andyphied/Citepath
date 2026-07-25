import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { sanitizeNextPath } from "@/lib/auth/safe-next";
import { hasAuthCookie } from "@/lib/auth/session";
import { isProtectedPath } from "@/lib/nav";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (!isProtectedPath(pathname)) {
    return NextResponse.next();
  }

  if (!hasAuthCookie(request.headers.get("cookie"))) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/login";
    loginUrl.searchParams.set("next", sanitizeNextPath(pathname));
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Protect app routes; skip Next internals and static assets.
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
