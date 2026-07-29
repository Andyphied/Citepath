"use client";

import { CitationList } from "@/components/ask/citation-list";
import type { AgentRunResponse } from "@/lib/api/types";
import {
  buildInvestigationSections,
  resolveRelatedDocuments,
} from "@/lib/agent/sections";

export function InvestigationResult({
  result,
}: Readonly<{ result: AgentRunResponse }>) {
  const summary = result.summary;
  if (!summary) {
    return (
      <p className="text-sm text-[var(--muted)]">
        Investigation finished without a structured summary.
      </p>
    );
  }

  const sections = buildInvestigationSections(summary);
  const citations = result.citations ?? [];
  const toolCallsLabel = formatToolCallsLabel(result.tool_calls_count);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-[family-name:var(--font-display)] text-lg text-[var(--ink)]">
          Investigation result
        </h3>
        <p className="text-xs text-[var(--muted)]">
          Status {result.status}
          {toolCallsLabel ? ` · ${toolCallsLabel}` : null}
        </p>
      </div>

      <div className="grid gap-4">
        {sections.map((section) => (
          <section
            key={section.field}
            className="rounded-md border border-[var(--border)] bg-[var(--surface)] p-4"
            aria-labelledby={`agent-section-${section.field}`}
          >
            <h4
              id={`agent-section-${section.field}`}
              className="text-sm font-semibold text-[var(--ink)]"
            >
              {section.title}
            </h4>
            <p className="mt-0.5 font-[family-name:var(--font-mono)] text-[0.65rem] text-[var(--muted)]">
              {section.field}
            </p>

            {section.kind === "text" ? (
              <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-[var(--ink)]">
                {section.text?.trim()
                  ? section.text
                  : "No summary content returned."}
              </p>
            ) : null}

            {section.kind === "list" ? (
              <StringList items={section.items ?? []} emptyLabel="None listed." />
            ) : null}

            {section.kind === "documents" ? (
              <RelatedDocumentsList
                documentIds={section.items ?? []}
                citations={citations}
              />
            ) : null}
          </section>
        ))}

        <section
          className="rounded-md border border-[var(--border)] bg-[var(--surface)] p-4"
          aria-labelledby="agent-section-sources"
        >
          <h4
            id="agent-section-sources"
            className="text-sm font-semibold text-[var(--ink)]"
          >
            Sources
          </h4>
          <p className="mt-0.5 font-[family-name:var(--font-mono)] text-[0.65rem] text-[var(--muted)]">
            citations
          </p>
          {citations.length > 0 ? (
            <CitationList citations={citations} />
          ) : (
            <p className="mt-3 text-sm text-[var(--muted)]">
              No cited sources returned.
            </p>
          )}
        </section>
      </div>
    </div>
  );
}

function formatToolCallsLabel(count: number): string | null {
  if (count <= 0) {
    return null;
  }
  return `${count} tool call${count === 1 ? "" : "s"}`;
}

function StringList({
  items,
  emptyLabel,
}: Readonly<{
  items: string[];
  emptyLabel: string;
}>) {
  if (items.length === 0) {
    return <p className="mt-3 text-sm text-[var(--muted)]">{emptyLabel}</p>;
  }

  return (
    <ul className="mt-3 list-disc space-y-1.5 pl-5 text-sm leading-relaxed text-[var(--ink)]">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

function RelatedDocumentsList({
  documentIds,
  citations,
}: Readonly<{
  documentIds: string[];
  citations: AgentRunResponse["citations"];
}>) {
  if (documentIds.length === 0) {
    return (
      <p className="mt-3 text-sm text-[var(--muted)]">None listed.</p>
    );
  }

  const docs = resolveRelatedDocuments(documentIds, citations);

  return (
    <ul className="mt-3 flex flex-col gap-2">
      {docs.map((doc) => (
        <li
          key={doc.document_id}
          className="rounded-md border border-[var(--border)] bg-[var(--canvas)] px-3 py-2"
        >
          <p className="text-sm font-medium text-[var(--ink)]">{doc.title}</p>
          <p className="mt-0.5 font-[family-name:var(--font-mono)] text-[0.65rem] text-[var(--muted)]">
            {doc.document_id}
          </p>
        </li>
      ))}
    </ul>
  );
}
