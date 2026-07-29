import { describe, expect, it } from "vitest";

import { shouldApplyAgentResponse } from "@/lib/agent/apply";
import {
  buildInvestigationSections,
  resolveRelatedDocuments,
} from "@/lib/agent/sections";
import type { InvestigationSummary } from "@/lib/api/types";

const summary: InvestigationSummary = {
  problem_statement: "Billing API returning 502 after deploy.",
  summary: "Likely upstream timeout in payment-gateway.",
  likely_causes: ["Deploy regression"],
  likely_related_systems: ["billing-api", "payment-gateway"],
  recommended_checks: ["Check recent deploy", "Inspect 5xx dashboards"],
  related_documents: [
    "11111111-1111-1111-1111-111111111111",
    "22222222-2222-2222-2222-222222222222",
  ],
  action_items: ["Page payments on-call"],
  risks_or_unknowns: ["Unknown traffic spike window"],
  next_steps: ["Roll back if error rate stays elevated"],
};

describe("buildInvestigationSections", () => {
  it("maps story labels onto InvestigationSummary API fields", () => {
    const sections = buildInvestigationSections(summary);

    expect(sections.map((section) => section.field)).toEqual([
      "summary",
      "likely_related_systems",
      "related_documents",
      "recommended_checks",
      "risks_or_unknowns",
      "next_steps",
    ]);

    expect(sections[0]).toMatchObject({
      title: "Summary",
      kind: "text",
      text: expect.stringContaining("Billing API returning 502"),
    });
    expect(sections[0]?.text).toContain("payment-gateway");

    expect(sections.find((s) => s.field === "recommended_checks")).toMatchObject(
      {
        title: "Suggested checks",
        items: ["Check recent deploy", "Inspect 5xx dashboards"],
      },
    );
    expect(
      sections.find((s) => s.field === "related_documents")?.items,
    ).toHaveLength(2);
  });

  it("does not invent fields beyond InvestigationSummary", () => {
    const fields = buildInvestigationSections(summary).map((s) => s.field);
    expect(fields).not.toContain("likely_causes");
    expect(fields).not.toContain("action_items");
    expect(fields).not.toContain("sources");
  });
});

describe("resolveRelatedDocuments", () => {
  it("uses citation titles when document_id matches", () => {
    const docs = resolveRelatedDocuments(
      [
        "11111111-1111-1111-1111-111111111111",
        "22222222-2222-2222-2222-222222222222",
      ],
      [
        {
          chunk_id: "c1",
          document_id: "11111111-1111-1111-1111-111111111111",
          document_title: "Billing 502 runbook",
          chunk_preview: "Check pods",
          score: 0.9,
        },
      ],
    );

    expect(docs[0]).toEqual({
      document_id: "11111111-1111-1111-1111-111111111111",
      title: "Billing 502 runbook",
    });
    expect(docs[1]?.title).toBe("22222222…");
  });
});

describe("shouldApplyAgentResponse", () => {
  it("applies when workspace is unchanged", () => {
    expect(shouldApplyAgentResponse("ws-1", "ws-1")).toBe(true);
  });

  it("discards when workspace changed mid-flight", () => {
    expect(shouldApplyAgentResponse("ws-1", "ws-2")).toBe(false);
    expect(shouldApplyAgentResponse("ws-1", null)).toBe(false);
  });
});
