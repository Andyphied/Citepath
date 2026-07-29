import { afterEach, describe, expect, it, vi } from "vitest";

import { askQuestion } from "@/lib/api/query";

describe("query API helpers", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("posts question without conversation_id on first turn", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          conversation_id: "conv-1",
          message_id: "msg-1",
          answer: "Check upstream billing-api.",
          confidence: "high",
          citations: [],
          suggested_followups: ["What changed in the last deploy?"],
          insufficient_context: false,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await askQuestion("ws-1", {
      question: "  What should I check for billing 502 errors?  ",
    });

    expect(result.conversation_id).toBe("conv-1");
    expect(result.insufficient_context).toBe(false);

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/workspaces/ws-1/query");
    expect(init.method).toBe("POST");
    const body = JSON.parse(String(init.body)) as Record<string, unknown>;
    expect(body).toEqual({
      question: "What should I check for billing 502 errors?",
    });
    expect(body).not.toHaveProperty("conversation_id");
  });

  it("includes conversation_id for follow-ups", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          conversation_id: "conv-1",
          message_id: "msg-2",
          answer: "Deploy rolled back.",
          confidence: "medium",
          citations: [],
          suggested_followups: [],
          insufficient_context: false,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await askQuestion("ws-1", {
      question: "What changed?",
      conversation_id: "conv-1",
    });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const body = JSON.parse(String(init.body)) as Record<string, unknown>;
    expect(body).toEqual({
      question: "What changed?",
      conversation_id: "conv-1",
    });
  });
});
