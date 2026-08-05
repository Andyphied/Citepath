import { describe, expect, it } from "vitest";

import { canAccessAdminDashboard } from "@/lib/admin/access";
import {
  formatCostUsd,
  formatTokenCount,
  jobStatusLabel,
} from "@/lib/admin/format";
import {
  failedJobErrorText,
  ingestionJobStatusTone,
  isAdminDashboardDataCurrent,
  shouldApplyAdminResponse,
} from "@/lib/admin/status";
import { isAdminRole } from "@/lib/api/types";
import type { AdminIngestionJobItem } from "@/lib/api/types";
import { PRIMARY_NAV } from "@/lib/nav";

describe("admin dashboard role gating", () => {
  it("allows owner and admin only", () => {
    expect(canAccessAdminDashboard("owner")).toBe(true);
    expect(canAccessAdminDashboard("admin")).toBe(true);
    expect(canAccessAdminDashboard("member")).toBe(false);
    expect(canAccessAdminDashboard("viewer")).toBe(false);
    expect(canAccessAdminDashboard(null)).toBe(false);
    expect(isAdminRole("viewer")).toBe(false);
  });

  it("marks Admin nav item as adminOnly", () => {
    const adminNav = PRIMARY_NAV.find((item) => item.href === "/admin");
    expect(adminNav?.adminOnly).toBe(true);
  });
});

describe("admin format helpers", () => {
  it("formats cost from Decimal string and number", () => {
    expect(formatCostUsd("0.001510")).toBe("$0.001510");
    expect(formatCostUsd(1.25)).toBe("$1.25");
    expect(formatCostUsd(0)).toBe("$0.00");
    expect(formatCostUsd("not-a-number")).toBe("$0.00");
  });

  it("formats token counts and job status labels", () => {
    expect(formatTokenCount(1234)).toBe("1,234");
    expect(jobStatusLabel("failed")).toBe("Failed");
    expect(jobStatusLabel("pending")).toBe("Pending");
  });
});

describe("admin status helpers", () => {
  it("maps failed job status to red tone", () => {
    expect(ingestionJobStatusTone("failed")).toBe("red");
    expect(ingestionJobStatusTone("completed")).toBe("green");
  });

  it("discards stale dashboard responses after workspace switch", () => {
    expect(shouldApplyAdminResponse("ws-a", "ws-a")).toBe(true);
    expect(shouldApplyAdminResponse("ws-a", "ws-b")).toBe(false);
    expect(shouldApplyAdminResponse("ws-a", null)).toBe(false);
  });

  it("treats dashboard data as current only for the active workspace", () => {
    expect(isAdminDashboardDataCurrent("ws-a", "ws-a")).toBe(true);
    expect(isAdminDashboardDataCurrent("ws-a", "ws-b")).toBe(false);
    expect(isAdminDashboardDataCurrent(null, "ws-b")).toBe(false);
    expect(isAdminDashboardDataCurrent("ws-a", null)).toBe(false);
  });

  it("surfaces failed-job error_message for the failed-jobs widget", () => {
    const withMessage = {
      id: "job-1",
      workspace_id: "ws-1",
      document_id: "doc-1",
      document_title: "runbook.md",
      status: "failed",
      attempt_count: 1,
      error_message: "  parse failed: invalid PDF  ",
      started_at: null,
      completed_at: null,
      created_at: "2026-08-04T12:00:00Z",
    } satisfies AdminIngestionJobItem;
    const withoutMessage = {
      ...withMessage,
      id: "job-2",
      error_message: null,
    } satisfies AdminIngestionJobItem;
    const blankMessage = {
      ...withMessage,
      id: "job-3",
      error_message: "   ",
    } satisfies AdminIngestionJobItem;

    expect(failedJobErrorText(withMessage)).toBe("parse failed: invalid PDF");
    expect(failedJobErrorText(withoutMessage)).toBe("Ingestion failed.");
    expect(failedJobErrorText(blankMessage)).toBe("Ingestion failed.");
  });
});
