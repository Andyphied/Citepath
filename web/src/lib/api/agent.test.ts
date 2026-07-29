import { afterEach, describe, expect, it, vi } from "vitest";

import {
  AGENT_TIMEOUT_CODE,
  startAgentRun,
} from "@/lib/api/agent";
import { ApiError } from "@/lib/api/client";

const sampleResponse = {
  agent_run_id: "run-1",
  status: "completed",
  summary: {
    problem_statement: "Billing 502",
    summary: "Upstream timeout likely.",
    likely_causes: [],
    likely_related_systems: ["billing-api"],
    recommended_checks: ["Check pods"],
    related_documents: ["doc-1"],
    action_items: [],
    risks_or_unknowns: ["Unknown deploy window"],
    next_steps: ["Page on-call"],
  },
  citations: [],
  tool_calls_count: 2,
};

describe("agent API helpers", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("posts trimmed objective without conversation_id by default", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(sampleResponse), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await startAgentRun("ws-1", {
      objective: "  Billing API returning 502 after deploy  ",
    });

    expect(result.agent_run_id).toBe("run-1");
    expect(result.summary?.likely_related_systems).toEqual(["billing-api"]);

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/workspaces/ws-1/agent-runs");
    expect(init.method).toBe("POST");
    expect(init.signal).toBeInstanceOf(AbortSignal);
    const body = JSON.parse(String(init.body)) as Record<string, unknown>;
    expect(body).toEqual({
      objective: "Billing API returning 502 after deploy",
    });
    expect(body).not.toHaveProperty("conversation_id");
  });

  it("includes conversation_id when provided", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(sampleResponse), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await startAgentRun("ws-1", {
      objective: "Investigate",
      conversation_id: "conv-1",
    });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const body = JSON.parse(String(init.body)) as Record<string, unknown>;
    expect(body).toEqual({
      objective: "Investigate",
      conversation_id: "conv-1",
    });
  });

  it("throws agent_timeout when the wall-clock limit elapses", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn(
      (_url: string, init?: RequestInit) =>
        new Promise<Response>((_resolve, reject) => {
          const signal = init?.signal;
          if (!signal) {
            reject(new Error("missing signal"));
            return;
          }
          signal.addEventListener("abort", () => {
            reject(new DOMException("Aborted", "AbortError"));
          });
        }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const pending = startAgentRun(
      "ws-1",
      { objective: "Slow investigation" },
      { timeoutMs: 50 },
    );
    // Attach rejection handler before advancing timers to avoid unhandled rejection.
    const assertion = expect(pending).rejects.toMatchObject({
      name: "ApiError",
      code: AGENT_TIMEOUT_CODE,
    });

    await vi.advanceTimersByTimeAsync(50);
    await assertion;
    await expect(pending).rejects.toBeInstanceOf(ApiError);
  });
});
