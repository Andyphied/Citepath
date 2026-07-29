"use client";

import { useState } from "react";

import type { CitationItem } from "@/lib/api/types";
import {
  citationDocumentTitle,
  formatCitationLocation,
} from "@/lib/ask/citation";

export function CitationList({ citations }: { citations: CitationItem[] }) {
  if (citations.length === 0) {
    return null;
  }

  return (
    <div className="mt-4">
      <h4 className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
        Citations ({citations.length})
      </h4>
      <ul className="mt-2 flex flex-col gap-2">
        {citations.map((citation, index) => (
          <CitationRow
            key={citation.chunk_id}
            citation={citation}
            index={index + 1}
          />
        ))}
      </ul>
    </div>
  );
}

function CitationRow({
  citation,
  index,
}: {
  citation: CitationItem;
  index: number;
}) {
  const [open, setOpen] = useState(index === 1);
  const location = formatCitationLocation(citation.metadata);
  const title = citationDocumentTitle(citation.document_title);

  return (
    <li className="rounded-md border border-[var(--border)] bg-[var(--surface)]">
      <button
        type="button"
        className="flex w-full items-start justify-between gap-3 px-3 py-2.5 text-left"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="min-w-0">
          <span className="text-xs font-medium text-[var(--accent)]">
            [{index}]
          </span>{" "}
          <span className="text-sm font-medium text-[var(--ink)]">{title}</span>
          {location ? (
            <span className="mt-0.5 block text-xs text-[var(--muted)]">
              {location}
            </span>
          ) : null}
        </span>
        <span className="shrink-0 text-xs text-[var(--muted)]">
          {open ? "Hide" : "Show"}
        </span>
      </button>
      {open ? (
        <div className="border-t border-[var(--border)] px-3 py-2.5">
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-[var(--muted)]">
            {citation.chunk_preview}
          </p>
          <p className="mt-2 text-[0.7rem] text-[var(--muted)]">
            Score {citation.score.toFixed(2)}
          </p>
        </div>
      ) : null}
    </li>
  );
}
