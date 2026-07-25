"use client";

import { WorkspaceSwitcher } from "@/components/workspace-switcher";
import { useWorkspace } from "@/components/workspace-provider";

export function Header({ title }: { title?: string }) {
  const { activeWorkspace } = useWorkspace();

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
      <WorkspaceSwitcher />
    </header>
  );
}
