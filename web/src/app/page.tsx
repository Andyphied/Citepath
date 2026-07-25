"use client";

import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { ErrorState } from "@/components/error-state";
import { LoadingState } from "@/components/loading-state";
import { useWorkspace } from "@/components/workspace-provider";

export default function HomePage() {
  const { user, loading: authLoading } = useAuth();
  const {
    workspaces,
    activeWorkspace,
    loading: workspaceLoading,
    error,
    refresh,
    workspacePath,
  } = useWorkspace();

  const loading = authLoading || workspaceLoading;

  return (
    <AppShell title="Home">
      <section className="max-w-2xl">
        <p className="font-[family-name:var(--font-display)] text-3xl text-[var(--ink)]">
          AtlasOps AI
        </p>
        <p className="mt-3 text-[var(--muted)] leading-relaxed">
          {user
            ? `Signed in as ${user.email}. Use the sidebar to open Documents, Ask, Agent, and Admin as feature pages land.`
            : "Shared app shell for the portfolio demo."}
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
          {!loading && !error && workspaces.length === 0 ? (
            <div className="border-t border-[var(--border)] pt-4">
              <p className="text-sm font-medium text-[var(--ink)]">
                No workspace yet
              </p>
              <p className="mt-2 text-sm text-[var(--muted)] leading-relaxed">
                Your account has no workspace memberships. Create one via{" "}
                <code className="font-[family-name:var(--font-mono)] text-xs">
                  POST /workspaces
                </code>{" "}
                (workspace creation UI arrives in a later story), then refresh
                this page or use the workspace switcher.
              </p>
              <button
                type="button"
                onClick={() => void refresh()}
                className="mt-4 rounded-md border border-[var(--border)] px-3 py-1.5 text-sm text-[var(--ink)] hover:border-[var(--border-strong)]"
              >
                Refresh workspaces
              </button>
            </div>
          ) : null}
        </div>
      </section>
    </AppShell>
  );
}
