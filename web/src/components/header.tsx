"use client";

import { useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";
import { useWorkspace } from "@/components/workspace-provider";

export function Header({ title }: { title?: string }) {
  const { user, logout } = useAuth();
  const { activeWorkspace } = useWorkspace();
  const [loggingOut, setLoggingOut] = useState(false);

  async function handleLogout() {
    if (loggingOut) {
      return;
    }
    setLoggingOut(true);
    try {
      await logout();
      // Full navigation so middleware re-evaluates cookie absence.
      window.location.assign("/login");
    } catch {
      setLoggingOut(false);
    }
  }

  return (
    <header className="flex h-14 items-center justify-between gap-4 border-b border-[var(--border)] bg-[var(--surface)] px-6">
      <div className="min-w-0">
        <h1 className="truncate font-[family-name:var(--font-display)] text-lg text-[var(--ink)]">
          {title ?? "Home"}
        </h1>
        {activeWorkspace ? (
          <p className="truncate text-xs text-[var(--muted)]">
            Role: {activeWorkspace.role}
          </p>
        ) : null}
      </div>
      <div className="flex min-w-0 items-center gap-4">
        {user ? (
          <div className="flex min-w-0 items-center gap-3">
            <p
              className="hidden truncate text-sm text-[var(--muted)] sm:block"
              title={user.email}
            >
              {user.email}
            </p>
            <button
              type="button"
              onClick={() => void handleLogout()}
              disabled={loggingOut}
              className="shrink-0 rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-sm text-[var(--ink)] hover:border-[var(--border-strong)] disabled:opacity-60"
            >
              {loggingOut ? "Signing out…" : "Log out"}
            </button>
          </div>
        ) : null}
        <WorkspaceSwitcher />
      </div>
    </header>
  );
}
