import { describe, expect, it } from "vitest";

import {
  resolveActiveWorkspaceId,
  workspaceApiPath,
} from "@/lib/workspace/storage";

describe("resolveActiveWorkspaceId", () => {
  it("keeps a still-valid stored workspace", () => {
    expect(
      resolveActiveWorkspaceId(["a", "b"], "b"),
    ).toBe("b");
  });

  it("falls back to the first workspace when stored id is stale", () => {
    expect(
      resolveActiveWorkspaceId(["a", "b"], "missing"),
    ).toBe("a");
  });

  it("returns null when the user has no workspaces", () => {
    expect(resolveActiveWorkspaceId([], "a")).toBeNull();
  });
});

describe("workspaceApiPath", () => {
  it("builds WS-006 style workspace-scoped paths", () => {
    expect(workspaceApiPath("ws-1")).toBe("/workspaces/ws-1");
    expect(workspaceApiPath("ws-1", "documents")).toBe(
      "/workspaces/ws-1/documents",
    );
    expect(workspaceApiPath("ws-1", "/query")).toBe("/workspaces/ws-1/query");
  });
});
