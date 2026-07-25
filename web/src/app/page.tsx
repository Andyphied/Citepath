"use client";

import { AppShell } from "@/components/app-shell";
import { ErrorState } from "@/components/error-state";
import { LoadingState } from "@/components/loading-state";
import { useWorkspace } from "@/components/workspace-provider";

export default function HomePage() {
  const { activeWorkspace, loading, error, refresh, workspacePath } =
    useWorkspace();

  return (
    <AppShell title="Home">
      <section className="max-w-2xl">
        <p className="font-[family-name:var(--font-display)] text-3xl text-[var(--ink)]">
          AtlasOps AI
        </p>
        <p className="mt-3 text-[var(--muted)] leading-relaxed">
          Shared app shell for the portfolio demo. Use the sidebar to open
          Documents, Ask, Agent, and Admin pages as later UI stories land.
        </p>

        <div className="mt-8 space-y-3">
          {loading ? <LoadingState label="Resolving workspace context…" /> : null}
          {error ? (
            <ErrorState
              title="API error"
              message={error}
              onRetry={() => void refresh()}
            />
          ) : null}
          {!loading && !error && activeWorkspace ? (
            <div className="border-t border-[var(--border)] pt-4 text-sm text-[var(--muted)]">
              <p>
                Active workspace:{" "}
                <span className="font-medium text-[var(--ink)]">
                  {activeWorkspace.name}
                </span>
              </p>
              <p className="mt-1 font-[family-name:var(--font-mono)] text-xs">
                Next API path: {workspacePath("documents")}
              </p>
            </div>
          ) : null}
        </div>
      </section>
    </AppShell>
  );
}
