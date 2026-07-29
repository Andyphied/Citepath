import type { CitationItem, QueryResponse } from "@/lib/api/types";

export type AskTurn = {
  id: string;
  question: string;
  answer: string;
  citations: CitationItem[];
  insufficient_context: boolean;
  confidence: string;
  suggested_followups: string[];
};

/** Append a Q&A pair from a successful query response. */
export function appendAskTurn(
  turns: AskTurn[],
  question: string,
  response: QueryResponse,
): AskTurn[] {
  return [
    ...turns,
    {
      id: response.message_id,
      question,
      answer: response.answer,
      citations: response.citations ?? [],
      insufficient_context: Boolean(response.insufficient_context),
      confidence: response.confidence,
      suggested_followups: response.suggested_followups ?? [],
    },
  ];
}

/** Latest suggested follow-ups from the thread (empty if none). */
export function latestFollowups(turns: AskTurn[]): string[] {
  if (turns.length === 0) {
    return [];
  }
  return turns[turns.length - 1]?.suggested_followups ?? [];
}

/**
 * Whether an in-flight ask response should update UI state.
 * Discard when the active workspace changed mid-request.
 */
export function shouldApplyAskResponse(
  requestWorkspaceId: string,
  activeWorkspaceId: string | null | undefined,
): boolean {
  return Boolean(
    activeWorkspaceId && activeWorkspaceId === requestWorkspaceId,
  );
}
