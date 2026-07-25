"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useWorkspace } from "@/components/workspace-provider";
import { isAdminRole } from "@/lib/api/types";
import { PRIMARY_NAV } from "@/lib/nav";

export function Sidebar() {
  const pathname = usePathname();
  const { activeWorkspace } = useWorkspace();
  const canAccessAdmin = isAdminRole(activeWorkspace?.role);

  return (
    <aside className="flex w-56 shrink-0 flex-col border-r border-[var(--sidebar-border)] bg-[var(--sidebar)] text-[var(--sidebar-ink)]">
      <div className="border-b border-[var(--sidebar-border)] px-5 py-5">
        <Link href="/" className="block">
          <p className="font-[family-name:var(--font-display)] text-xl tracking-tight text-white">
            AtlasOps AI
          </p>
          <p className="mt-1 text-xs text-[var(--sidebar-muted)]">
            Workspace knowledge ops
          </p>
        </Link>
      </div>

      <nav className="flex flex-1 flex-col gap-1 px-3 py-4" aria-label="Primary">
        {PRIMARY_NAV.map((item) => {
          const active =
            pathname === item.href || pathname.startsWith(`${item.href}/`);
          const disabled = Boolean(item.adminOnly && !canAccessAdmin);

          if (disabled) {
            return (
              <span
                key={item.href}
                className="cursor-not-allowed rounded-md px-3 py-2 text-sm text-[var(--sidebar-muted)] opacity-50"
                title="Requires owner or admin role in the active workspace"
              >
                {item.label}
              </span>
            );
          }

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`rounded-md px-3 py-2 text-sm transition-colors ${
                active
                  ? "bg-[var(--sidebar-active)] text-white"
                  : "text-[var(--sidebar-ink)] hover:bg-[var(--sidebar-hover)] hover:text-white"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-[var(--sidebar-border)] px-4 py-3 text-xs text-[var(--sidebar-muted)]">
        Demo UI · session via /auth/me
      </div>
    </aside>
  );
}
