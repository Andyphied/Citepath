import { ApiError, apiFetch } from "@/lib/api/client";
import type { AgentRunRequest, AgentRunResponse } from "@/lib/api/types";

/** Client-side wall-clock timeout aligned with agent architecture (~120s). */
export const AGENT_RUN_TIMEOUT_MS = 120_000;

export const AGENT_TIMEOUT_CODE = "agent_timeout";

export type StartAgentRunOptions = {
  /** Override default 120s timeout (tests). */
  timeoutMs?: number;
  /** Optional external abort (tests). */
  signal?: AbortSignal;
};

/**
 * POST /workspaces/{id}/agent-runs — sync investigation (may take up to ~120s).
 * Aborts and throws `agent_timeout` when the wall-clock limit elapses.
 */
export async function startAgentRun(
  workspaceId: string,
  body: AgentRunRequest,
  options: StartAgentRunOptions = {},
): Promise<AgentRunResponse> {
  const timeoutMs = options.timeoutMs ?? AGENT_RUN_TIMEOUT_MS;
  const controller = new AbortController();
  const onExternalAbort = () => controller.abort();
  if (options.signal) {
    if (options.signal.aborted) {
      controller.abort();
    } else {
      options.signal.addEventListener("abort", onExternalAbort, { once: true });
    }
  }

  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const payload: AgentRunRequest = {
    objective: body.objective.trim(),
  };
  if (body.conversation_id) {
    payload.conversation_id = body.conversation_id;
  }

  try {
    return await apiFetch<AgentRunResponse>(
      `/workspaces/${workspaceId}/agent-runs`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal: controller.signal,
      },
    );
  } catch (err) {
    if (controller.signal.aborted && !options.signal?.aborted) {
      throw new ApiError(
        0,
        AGENT_TIMEOUT_CODE,
        "Investigation timed out after 120 seconds. You can retry.",
      );
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
    options.signal?.removeEventListener("abort", onExternalAbort);
  }
}
