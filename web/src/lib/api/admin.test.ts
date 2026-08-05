import { afterEach, describe, expect, it, vi } from "vitest";

import {
  getDocumentsOverview,
  getFailedJobsWidget,
  getWorkspaceUsageSummary,
  listIngestionJobs,
} from "@/lib/api/admin";

describe("admin API helpers", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("fetches documents overview", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          workspace_id: "ws-1",
          total: 2,
          by_status: {
            uploaded: 0,
            processing: 0,
            indexed: 2,
            failed: 0,
          },
          recent_uploads: [],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await getDocumentsOverview("ws-1");

    expect(result.total).toBe(2);
    const [url] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/workspaces/ws-1/admin/documents-overview");
  });

  it("lists ingestion jobs with pagination and status filter", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          items: [],
          total: 0,
          page: 1,
          page_size: 20,
          pending_count: 0,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await listIngestionJobs("ws-1", {
      page: 1,
      pageSize: 20,
      status: "failed",
    });

    const [url] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/workspaces/ws-1/admin/ingestion-jobs?");
    expect(url).toContain("page=1");
    expect(url).toContain("page_size=20");
    expect(url).toContain("status=failed");
  });

  it("fetches failed-jobs widget", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          failed_last_24h: 1,
          failed_last_7d: 2,
          items: [],
          empty_message: null,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await getFailedJobsWidget("ws-1");

    expect(result.failed_last_7d).toBe(2);
    const [url] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/workspaces/ws-1/admin/failed-jobs");
  });

  it("fetches usage summary with optional date range", async () => {
    const usageBody = {
      workspace_id: "ws-1",
      from: "2026-07-28T00:00:00Z",
      to: "2026-08-04T00:00:00Z",
      totals: {
        prompt_tokens: 10,
        completion_tokens: 5,
        embedding_tokens: 0,
        estimated_cost_usd: "0.001510",
        call_count: 3,
      },
      by_day: [],
      by_operation: [],
    };
    const fetchMock = vi.fn().mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify(usageBody), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const defaultWindow = await getWorkspaceUsageSummary("ws-1");
    expect(defaultWindow.totals.call_count).toBe(3);
    expect(fetchMock.mock.calls[0]?.[0]).toContain(
      "/workspaces/ws-1/admin/usage",
    );
    expect(String(fetchMock.mock.calls[0]?.[0])).not.toContain("from=");

    await getWorkspaceUsageSummary("ws-1", {
      from: "2026-07-01T00:00:00Z",
      to: "2026-08-01T00:00:00Z",
    });
    const rangedUrl = String(fetchMock.mock.calls[1]?.[0]);
    expect(rangedUrl).toContain("from=2026-07-01T00%3A00%3A00Z");
    expect(rangedUrl).toContain("to=2026-08-01T00%3A00%3A00Z");
  });
});
