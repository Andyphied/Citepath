import type { CitationItem, InvestigationSummary } from "@/lib/api/types";
import { citationDocumentTitle } from "@/lib/ask/citation";

export type InvestigationSectionKind = "text" | "list" | "documents";

export type InvestigationSection = {
  /** API field name from InvestigationSummary (or citations for Sources). */
  field: string;
  /** Story / demo heading mapped to that field. */
  title: string;
  kind: InvestigationSectionKind;
  text?: string;
  items?: string[];
};

export type RelatedDocumentItem = {
  document_id: string;
  title: string;
};

/**
 * Map AGENT-008 / story section labels onto InvestigationSummary fields.
 * Does not invent fields — only reads known schema keys.
 */
export function buildInvestigationSections(
  summary: InvestigationSummary,
): InvestigationSection[] {
  return [
    {
      field: "summary",
      title: "Summary",
      kind: "text",
      text: formatSummaryText(summary),
    },
    {
      field: "likely_related_systems",
      title: "Likely related systems",
      kind: "list",
      items: summary.likely_related_systems ?? [],
    },
    {
      field: "related_documents",
      title: "Relevant documents",
      kind: "documents",
      items: (summary.related_documents ?? []).map(String),
    },
    {
      field: "recommended_checks",
      title: "Suggested checks",
      kind: "list",
      items: summary.recommended_checks ?? [],
    },
    {
      field: "risks_or_unknowns",
      title: "Risks / unknowns",
      kind: "list",
      items: summary.risks_or_unknowns ?? [],
    },
    {
      field: "next_steps",
      title: "Next steps",
      kind: "list",
      items: summary.next_steps ?? [],
    },
  ];
}

function formatSummaryText(summary: InvestigationSummary): string {
  const problem = summary.problem_statement?.trim() ?? "";
  const body = summary.summary?.trim() ?? "";
  if (problem && body) {
    return `${problem}\n\n${body}`;
  }
  return body || problem;
}

/** Resolve related_documents UUIDs to titles using citation document_id matches. */
export function resolveRelatedDocuments(
  documentIds: string[],
  citations: CitationItem[],
): RelatedDocumentItem[] {
  const titleById = new Map<string, string>();
  for (const citation of citations) {
    if (!citation.document_id || titleById.has(citation.document_id)) {
      continue;
    }
    titleById.set(
      citation.document_id,
      citationDocumentTitle(citation.document_title),
    );
  }

  return documentIds.map((document_id) => ({
    document_id,
    title: titleById.get(document_id) ?? shortDocumentId(document_id),
  }));
}

function shortDocumentId(id: string): string {
  const trimmed = id.trim();
  if (trimmed.length <= 12) {
    return trimmed || "Unknown document";
  }
  return `${trimmed.slice(0, 8)}…`;
}
