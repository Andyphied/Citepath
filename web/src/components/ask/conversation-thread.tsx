"use client";

import { MarkdownAnswer } from "@/components/ask/markdown-answer";
import { CitationList } from "@/components/ask/citation-list";
import type { AskTurn } from "@/lib/ask/thread";

export function ConversationThread({ turns }: { turns: AskTurn[] }) {
  if (turns.length === 0) {
    return null;
  }

  return (
    <ol className="flex flex-col gap-5">
      {turns.map((turn, index) => (
        <li
          key={turn.id}
          className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-4 py-4"
        >
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
            Question {index + 1}
          </p>
          <p className="mt-1 text-sm font-medium text-[var(--ink)]">
            {turn.question}
          </p>

          <div className="mt-4 border-t border-[var(--border)] pt-4">
            {turn.insufficient_context ? (
              <InsufficientContextBanner answer={turn.answer} />
            ) : (
              <>
                <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                  Answer
                  {turn.confidence ? (
                    <span className="ml-2 font-normal normal-case tracking-normal">
                      · confidence {turn.confidence}
                    </span>
                  ) : null}
                </p>
                <div className="mt-2">
                  <MarkdownAnswer text={turn.answer} />
                </div>
                <CitationList citations={turn.citations} />
              </>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}

function InsufficientContextBanner({ answer }: { answer: string }) {
  return (
    <div
      className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
      role="status"
    >
      <p className="font-medium">Insufficient context</p>
      <p className="mt-1 leading-relaxed text-amber-900/90">{answer}</p>
      <p className="mt-2 text-xs text-amber-800/80">
        This is not an error — the knowledge base did not return enough relevant
        chunks to ground an answer.
      </p>
    </div>
  );
}
