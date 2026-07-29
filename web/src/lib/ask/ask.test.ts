import { describe, expect, it } from "vitest";

import {
  citationDocumentTitle,
  formatCitationLocation,
} from "@/lib/ask/citation";
import { escapeHtml, markdownToSafeHtml } from "@/lib/ask/markdown";
import { readAskPrefill } from "@/lib/ask/prefill";
import {
  appendAskTurn,
  latestFollowups,
  shouldApplyAskResponse,
} from "@/lib/ask/thread";

describe("readAskPrefill", () => {
  it("reads and trims q param", () => {
    expect(readAskPrefill("?q=billing+502")).toBe("billing 502");
    expect(readAskPrefill("q=hello%20world")).toBe("hello world");
  });

  it("returns empty when q is missing", () => {
    expect(readAskPrefill("")).toBe("");
    expect(readAskPrefill("?foo=bar")).toBe("");
  });
});

describe("citation helpers", () => {
  it("formats page and section metadata", () => {
    expect(
      formatCitationLocation({
        page_number: 3,
        section_heading: "Billing 502",
      }),
    ).toBe("p. 3 · Billing 502");
  });

  it("falls back for missing titles", () => {
    expect(citationDocumentTitle(null)).toBe("Untitled document");
    expect(citationDocumentTitle("  Runbook  ")).toBe("Runbook");
  });
});

describe("markdown helpers", () => {
  it("escapes raw HTML before formatting", () => {
    expect(escapeHtml(`<script>alert("x")</script>`)).toContain("&lt;script&gt;");
    const html = markdownToSafeHtml(
      'Hello **world** and <img src=x onerror=alert(1)>',
    );
    expect(html).toContain("<strong>world</strong>");
    expect(html).not.toContain("<img");
    expect(html).toContain("&lt;img");
  });

  it("renders lists and paragraphs", () => {
    const html = markdownToSafeHtml(
      "Checks:\n\n- Verify pods\n- Check logs\n\nDone.",
    );
    expect(html).toContain("<ul>");
    expect(html).toContain("<li>Verify pods</li>");
    expect(html).toContain("<p>Done.</p>");
  });
});

describe("thread helpers", () => {
  it("appends turns and exposes latest followups", () => {
    const turns = appendAskTurn([], "Q1", {
      conversation_id: "c1",
      message_id: "m1",
      answer: "A1",
      confidence: "high",
      citations: [],
      suggested_followups: ["Follow A"],
      insufficient_context: false,
    });
    const next = appendAskTurn(turns, "Q2", {
      conversation_id: "c1",
      message_id: "m2",
      answer: "A2",
      confidence: "low",
      citations: [],
      suggested_followups: ["Follow B"],
      insufficient_context: true,
    });
    expect(next).toHaveLength(2);
    expect(next[1]?.insufficient_context).toBe(true);
    expect(latestFollowups(next)).toEqual(["Follow B"]);
  });
});

describe("shouldApplyAskResponse", () => {
  it("applies when the active workspace still matches the request workspace", () => {
    expect(shouldApplyAskResponse("ws-a", "ws-a")).toBe(true);
  });

  it("discards when the workspace changed mid-flight", () => {
    expect(shouldApplyAskResponse("ws-a", "ws-b")).toBe(false);
  });

  it("discards when there is no active workspace after the request", () => {
    expect(shouldApplyAskResponse("ws-a", null)).toBe(false);
    expect(shouldApplyAskResponse("ws-a", undefined)).toBe(false);
  });
});
