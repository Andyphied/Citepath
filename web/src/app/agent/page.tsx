"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { InvestigationResult } from "@/components/agent/investigation-result";
import { AppShell } from "@/components/app-shell";
import { ErrorState } from "@/components/error-state";
import { FeedbackBanner } from "@/components/feedback-banner";
import { LoadingState } from "@/components/loading-state";
import { useWorkspace } from "@/components/workspace-provider";
import { shouldApplyAgentResponse } from "@/lib/agent/apply";
import {
  AGENT_TIMEOUT_CODE,
  startAgentRun,
} from "@/lib/api/agent";
import { ApiError } from "@/lib/api/client";
import type { AgentRunResponse } from "@/lib/api/types";
import { AGENT_DEMO_PROMPTS } from "@/lib/demo/prompts";

function errorMessage(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback;
}

export default function AgentPage() {
  const {
    activeWorkspaceId,
    loading: workspaceLoading,
    error: workspaceError,
    refresh: refreshWorkspaces,
  } = useWorkspace();

  const [objective, setObjective] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<AgentRunResponse | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const [lastSubmittedObjective, setLastSubmittedObjective] = useState<
    string | null
  >(null);
  const activeWorkspaceIdRef = useRef(activeWorkspaceId);
  activeWorkspaceIdRef.current = activeWorkspaceId;

  useEffect(() => {
    setResult(null);
    setRunError(null);
    setLastSubmittedObjective(null);
  }, [activeWorkspaceId]);

  const startInvestigation = useCallback(
    async (rawObjective: string) => {
      const trimmed = rawObjective.trim();
      const requestWorkspaceId = activeWorkspaceId;
      if (!requestWorkspaceId || !trimmed || running) {
        return;
      }

      setRunning(true);
      setRunError(null);
      setResult(null);
      setLastSubmittedObjective(trimmed);

      try {
        const response = await startAgentRun(requestWorkspaceId, {
          objective: trimmed,
        });
        if (
          !shouldApplyAgentResponse(
            requestWorkspaceId,
            activeWorkspaceIdRef.current,
          )
        ) {
          return;
        }
        setResult(response);
      } catch (err) {
        if (
          !shouldApplyAgentResponse(
            requestWorkspaceId,
            activeWorkspaceIdRef.current,
          )
        ) {
          return;
        }
        const fallback =
          err instanceof ApiError && err.code === AGENT_TIMEOUT_CODE
            ? "Investigation timed out after 120 seconds. You can retry."
            : "Investigation failed. Try again.";
        setRunError(errorMessage(err, fallback));
      } finally {
        setRunning(false);
      }
    },
    [activeWorkspaceId, running],
  );

  const canStart =
    Boolean(activeWorkspaceId) && objective.trim().length > 0 && !running;

  return (
    <AppShell title="Agent">
      <section className="mx-auto flex w-full max-w-5xl flex-col gap-6">
        <div>
          <h2 className="font-[family-name:var(--font-display)] text-2xl text-[var(--ink)]">
            Agent
          </h2>
          <p className="mt-2 text-sm text-[var(--muted)] leading-relaxed">
            Run a structured incident investigation against the workspace
            knowledge base.
          </p>
        </div>

        {workspaceLoading ? (
          <LoadingState label="Loading workspace…" />
        ) : null}

        {workspaceError ? (
          <ErrorState
            title="Workspace error"
            message={workspaceError}
            onRetry={() => {
              void refreshWorkspaces();
            }}
          />
        ) : null}

        {!workspaceLoading && !workspaceError && !activeWorkspaceId ? (
          <p className="text-sm text-[var(--muted)]">
            Select or create a workspace to run an investigation.
          </p>
        ) : null}

        {activeWorkspaceId ? (
          <form
            className="rounded-md border border-[var(--border)] bg-[var(--surface)] p-4"
            onSubmit={(event) => {
              event.preventDefault();
              void startInvestigation(objective);
            }}
          >
            <label
              htmlFor="agent-objective"
              className="block text-sm font-medium text-[var(--ink)]"
            >
              Objective
            </label>
            <textarea
              id="agent-objective"
              rows={5}
              value={objective}
              disabled={running}
              placeholder="Billing API returning 502 after deploy — investigate likely causes and checks."
              className="mt-2 w-full resize-y rounded-md border border-[var(--border)] bg-[var(--canvas)] px-3 py-2 text-sm text-[var(--ink)] outline-none ring-[var(--accent)] placeholder:text-[var(--muted)] focus:ring-2 disabled:opacity-60"
              onChange={(event) => setObjective(event.target.value)}
              onKeyDown={(event) => {
                if (
                  (event.metaKey || event.ctrlKey) &&
                  event.key === "Enter" &&
                  canStart
                ) {
                  event.preventDefault();
                  void startInvestigation(objective);
                }
              }}
            />
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <button
                type="submit"
                disabled={!canStart}
                className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white transition enabled:hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {running ? "Investigating…" : "Start investigation"}
              </button>
            </div>
          </form>
        ) : null}

        {running ? (
          <LoadingState label="Running investigation… this can take up to ~120 seconds." />
        ) : null}

        {runError ? (
          <div className="flex flex-col gap-3">
            <FeedbackBanner
              tone="error"
              message={runError}
              onDismiss={() => setRunError(null)}
            />
            {lastSubmittedObjective ? (
              <button
                type="button"
                disabled={running || !activeWorkspaceId}
                className="w-fit rounded-md border border-[var(--border)] bg-[var(--surface)] px-4 py-2 text-sm font-medium text-[var(--ink)] transition hover:border-[var(--accent)] hover:bg-[var(--accent-soft)] disabled:cursor-not-allowed disabled:opacity-50"
                onClick={() => {
                  setObjective(lastSubmittedObjective);
                  void startInvestigation(lastSubmittedObjective);
                }}
              >
                Retry investigation
              </button>
            ) : null}
          </div>
        ) : null}

        {!running && result ? <InvestigationResult result={result} /> : null}

        {activeWorkspaceId && !running && !result && !runError ? (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
              Try a Northstar investigation
            </p>
            <div className="mt-2 flex flex-col gap-2">
              {AGENT_DEMO_PROMPTS.map((item) => (
                <button
                  key={item}
                  type="button"
                  disabled={running || !activeWorkspaceId}
                  className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-left text-sm text-[var(--ink)] transition hover:border-[var(--accent)] hover:bg-[var(--accent-soft)] disabled:opacity-50"
                  onClick={() => {
                    setObjective(item);
                    void startInvestigation(item);
                  }}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
        ) : null}
      </section>
    </AppShell>
  );
}
