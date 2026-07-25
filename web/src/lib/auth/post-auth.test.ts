import { describe, expect, it } from "vitest";

import { resolvePostAuthPath } from "@/lib/auth/post-auth";

describe("resolvePostAuthPath", () => {
  it("defaults to home", () => {
    expect(resolvePostAuthPath(null)).toBe("/");
    expect(resolvePostAuthPath("")).toBe("/");
  });

  it("keeps safe same-app paths", () => {
    expect(resolvePostAuthPath("/documents")).toBe("/documents");
    expect(resolvePostAuthPath("/ask")).toBe("/ask");
  });

  it("rejects open redirects via sanitizeNextPath", () => {
    expect(resolvePostAuthPath("//evil.example")).toBe("/");
    expect(resolvePostAuthPath("https://evil.example")).toBe("/");
    expect(resolvePostAuthPath("/\\evil")).toBe("/");
  });
});
