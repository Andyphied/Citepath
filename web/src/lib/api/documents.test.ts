import { afterEach, describe, expect, it, vi } from "vitest";

import { listDocuments, uploadDocument } from "@/lib/api/documents";

describe("documents API helpers", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("lists documents with pagination query params", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          items: [],
          total: 0,
          page: 1,
          page_size: 50,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await listDocuments("ws-1", { page: 1, pageSize: 50, status: "indexed" });

    const [url] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/workspaces/ws-1/documents?");
    expect(url).toContain("page=1");
    expect(url).toContain("page_size=50");
    expect(url).toContain("status=indexed");
  });

  it("uploads via multipart FormData without JSON Content-Type", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          document: {
            id: "doc-1",
            workspace_id: "ws-1",
            title: "billing-api-runbook.md",
            source_type: "general",
            file_type: "md",
            status: "uploaded",
            status_label: "Uploaded",
            uploaded_by: "user-1",
            created_at: "2026-07-28T12:00:00Z",
            updated_at: "2026-07-28T12:00:00Z",
          },
          ingestion_job: { id: "job-1", status: "pending" },
        }),
        { status: 202, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const file = new File(["# billing"], "billing-api-runbook.md", {
      type: "text/markdown",
    });
    const result = await uploadDocument("ws-1", file, {
      title: "Billing API Runbook",
    });

    expect(result.document.status).toBe("uploaded");
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe("POST");
    expect(init.body).toBeInstanceOf(FormData);
    const headers = new Headers(init.headers);
    expect(headers.get("Content-Type")).toBeNull();
    const form = init.body as FormData;
    expect(form.get("file")).toBeInstanceOf(File);
    expect(form.get("title")).toBe("Billing API Runbook");
  });
});
