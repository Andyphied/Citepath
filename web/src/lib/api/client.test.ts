import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiFetch } from "@/lib/api/client";

describe("apiFetch", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("injects Authorization bearer token", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await apiFetch<{ ok: boolean }>("/workspaces", {
      baseUrl: "http://api.test",
      token: "test-jwt",
    });

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://api.test/workspaces");
    const headers = new Headers(init.headers);
    expect(headers.get("Authorization")).toBe("Bearer test-jwt");
  });

  it("maps structured API errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: "unauthorized",
              message: "Missing credentials",
              details: {},
            },
          }),
          { status: 401, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    await expect(
      apiFetch("/workspaces", { baseUrl: "http://api.test", token: null }),
    ).rejects.toMatchObject({
      name: "ApiError",
      status: 401,
      code: "unauthorized",
      message: "Missing credentials",
    } satisfies Partial<ApiError>);
  });

  it("surfaces network failures as ApiError", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
    );

    await expect(
      apiFetch("/workspaces", { baseUrl: "http://api.test", token: "x" }),
    ).rejects.toMatchObject({
      code: "network_error",
      status: 0,
    });
  });

  it("does not force Content-Type for FormData bodies", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 202,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const body = new FormData();
    body.append("file", new File(["# runbook"], "billing-api-runbook.md"));

    await apiFetch("/workspaces/ws-1/documents", {
      method: "POST",
      baseUrl: "http://api.test",
      token: "test-jwt",
      body,
      headers: { "Content-Type": "application/json" },
    });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = new Headers(init.headers);
    expect(headers.get("Content-Type")).toBeNull();
    expect(headers.get("Authorization")).toBe("Bearer test-jwt");
    expect(init.body).toBeInstanceOf(FormData);
  });
});
