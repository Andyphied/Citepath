"use client";

import { ErrorState } from "@/components/error-state";
import { LoadingState } from "@/components/loading-state";
import { useWorkspace } from "@/components/workspace-provider";

export function WorkspaceSwitcher() {
  const {
    workspaces,
    activeWorkspaceId,
    setActiveWorkspaceId,
    loading,
    error,
    refresh,
  } = useWorkspace();

  if (loading) {
    return <LoadingState label="Loading workspaces…" />;
  }

  if (error) {
    return (
      <ErrorState
        title="Workspaces unavailable"
        message={error}
        onRetry={() => void refresh()}
      />
    );
  }

  if (workspaces.length === 0) {
    return (
      <p className="text-sm text-[var(--muted)]">No workspaces yet</p>
    );
  }

  return (
    <label className="flex min-w-0 items-center gap-2 text-sm">
      <span className="shrink-0 text-[var(--muted)]">Workspace</span>
      <select
        className="max-w-[14rem] truncate rounded-md border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1.5 text-[var(--ink)] outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]"
        value={activeWorkspaceId ?? ""}
        onChange={(event) => setActiveWorkspaceId(event.target.value)}
        aria-label="Active workspace"
      >
        {workspaces.map((workspace) => (
          <option key={workspace.id} value={workspace.id}>
            {workspace.name}
          </option>
        ))}
      </select>
    </label>
  );
}
