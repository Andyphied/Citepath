"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { ConversationThread } from "@/components/ask/conversation-thread";
import { ErrorState } from "@/components/error-state";
import { FeedbackBanner } from "@/components/feedback-banner";
import { LoadingState } from "@/components/loading-state";
import { useWorkspace } from "@/components/workspace-provider";
import { ApiError } from "@/lib/api/client";
import { askQuestion } from "@/lib/api/query";
import { readAskPrefill } from "@/lib/ask/prefill";
import {
  appendAskTurn,
  latestFollowups,
  shouldApplyAskResponse,
  type AskTurn,
} from "@/lib/ask/thread";

function errorMessage(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback;
}

export default function AskPage() {
  const {
    activeWorkspaceId,
    loading: workspaceLoading,
    error: workspaceError,
    refresh: refreshWorkspaces,
  } = useWorkspace();

  const [question, setQuestion] = useState("");
  const [prefillApplied, setPrefillApplied] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [turns, setTurns] = useState<AskTurn[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const activeWorkspaceIdRef = useRef(activeWorkspaceId);
  activeWorkspaceIdRef.current = activeWorkspaceId;

  useEffect(() => {
    if (prefillApplied || typeof window === "undefined") {
      return;
    }
    const prefill = readAskPrefill(window.location.search);
    if (prefill) {
      setQuestion(prefill);
    }
    setPrefillApplied(true);
  }, [prefillApplied]);

  useEffect(() => {
    setConversationId(null);
    setTurns([]);
    setSubmitError(null);
  }, [activeWorkspaceId]);

  const submitQuestion = useCallback(
    async (rawQuestion: string) => {
      const trimmed = rawQuestion.trim();
      const requestWorkspaceId = activeWorkspaceId;
      if (!requestWorkspaceId || !trimmed || submitting) {
        return;
      }

      const requestConversationId = conversationId;

      setSubmitting(true);
      setSubmitError(null);
      try {
        const response = await askQuestion(requestWorkspaceId, {
          question: trimmed,
          conversation_id: requestConversationId,
        });
        if (
          !shouldApplyAskResponse(
            requestWorkspaceId,
            activeWorkspaceIdRef.current,
          )
        ) {
          return;
        }
        setConversationId(response.conversation_id);
        setTurns((prev) => appendAskTurn(prev, trimmed, response));
        setQuestion("");
      } catch (err) {
        if (
          !shouldApplyAskResponse(
            requestWorkspaceId,
            activeWorkspaceIdRef.current,
          )
        ) {
          return;
        }
        setSubmitError(
          errorMessage(err, "Failed to get an answer. Try again."),
        );
      } finally {
        setSubmitting(false);
      }
    },
    [activeWorkspaceId, conversationId, submitting],
  );

  const followups = latestFollowups(turns);
  const canSubmit =
    Boolean(activeWorkspaceId) && question.trim().length > 0 && !submitting;

  return (
    <AppShell title="Ask">
      <section className="mx-auto flex w-full max-w-5xl flex-col gap-6">
        <div>
          <h2 className="font-[family-name:var(--font-display)] text-2xl text-[var(--ink)]">
            Ask
          </h2>
          <p className="mt-2 text-sm text-[var(--muted)] leading-relaxed">
            Ask grounded questions and review cited answers from the workspace
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
            Select or create a workspace to ask questions.
          </p>
        ) : null}

        {activeWorkspaceId ? (
          <form
            className="rounded-md border border-[var(--border)] bg-[var(--surface)] p-4"
            onSubmit={(event) => {
              event.preventDefault();
              void submitQuestion(question);
            }}
          >
            <label
              htmlFor="ask-question"
              className="block text-sm font-medium text-[var(--ink)]"
            >
              Question
            </label>
            <textarea
              id="ask-question"
              rows={4}
              value={question}
              disabled={submitting}
              placeholder="What should I check for billing 502 errors?"
              className="mt-2 w-full resize-y rounded-md border border-[var(--border)] bg-[var(--canvas)] px-3 py-2 text-sm text-[var(--ink)] outline-none ring-[var(--accent)] placeholder:text-[var(--muted)] focus:ring-2 disabled:opacity-60"
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => {
                if (
                  (event.metaKey || event.ctrlKey) &&
                  event.key === "Enter" &&
                  canSubmit
                ) {
                  event.preventDefault();
                  void submitQuestion(question);
                }
              }}
            />
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <button
                type="submit"
                disabled={!canSubmit}
                className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white transition enabled:hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {submitting ? "Searching…" : "Ask"}
              </button>
              {conversationId ? (
                <button
                  type="button"
                  disabled={submitting}
                  className="text-sm text-[var(--muted)] underline underline-offset-2 hover:text-[var(--ink)] hover:no-underline disabled:opacity-50"
                  onClick={() => {
                    setConversationId(null);
                    setTurns([]);
                    setSubmitError(null);
                  }}
                >
                  Start new conversation
                </button>
              ) : null}
            </div>
          </form>
        ) : null}

        {submitting ? (
          <LoadingState label="Searching knowledge base…" />
        ) : null}

        {submitError ? (
          <FeedbackBanner
            tone="error"
            message={submitError}
            onDismiss={() => setSubmitError(null)}
          />
        ) : null}

        {turns.length > 0 ? <ConversationThread turns={turns} /> : null}

        {!submitting && followups.length > 0 ? (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
              Suggested follow-ups
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              {followups.map((item) => (
                <button
                  key={item}
                  type="button"
                  disabled={submitting || !activeWorkspaceId}
                  className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-left text-sm text-[var(--ink)] transition hover:border-[var(--accent)] hover:bg-[var(--accent-soft)] disabled:opacity-50"
                  onClick={() => {
                    void submitQuestion(item);
                  }}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {activeWorkspaceId &&
        !submitting &&
        turns.length === 0 &&
        !submitError ? (
          <p className="text-sm text-[var(--muted)] leading-relaxed">
            Tip: open{" "}
            <code className="rounded bg-[var(--accent-soft)] px-1 py-0.5 font-[family-name:var(--font-mono)] text-xs">
              /ask?q=billing+502
            </code>{" "}
            to prefill a demo question.
          </p>
        ) : null}
      </section>
    </AppShell>
  );
}
