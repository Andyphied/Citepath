import { apiFetch } from "@/lib/api/client";
import type { QueryRequest, QueryResponse } from "@/lib/api/types";

/** POST /workspaces/{id}/query — sync RAG answer with citations. */
export function askQuestion(
  workspaceId: string,
  body: QueryRequest,
): Promise<QueryResponse> {
  const payload: QueryRequest = {
    question: body.question.trim(),
  };
  if (body.conversation_id) {
    payload.conversation_id = body.conversation_id;
  }
  return apiFetch<QueryResponse>(`/workspaces/${workspaceId}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
