import { describe, expect, it } from "vitest";

import { sanitizeNextPath } from "@/lib/auth/safe-next";

describe("sanitizeNextPath", () => {
  it("allows same-app relative paths", () => {
    expect(sanitizeNextPath("/documents")).toBe("/documents");
    expect(sanitizeNextPath("/ask")).toBe("/ask");
    expect(sanitizeNextPath("/admin")).toBe("/admin");
    expect(sanitizeNextPath("/")).toBe("/");
    expect(sanitizeNextPath("/documents?tab=all")).toBe("/documents?tab=all");
  });

  it("rejects protocol-relative URLs", () => {
    expect(sanitizeNextPath("//evil.example")).toBe("/");
    expect(sanitizeNextPath("//evil.example/path")).toBe("/");
  });

  it("rejects absolute URLs", () => {
    expect(sanitizeNextPath("https://evil.example")).toBe("/");
    expect(sanitizeNextPath("http://evil.example/phish")).toBe("/");
    expect(sanitizeNextPath("https://evil.example/documents")).toBe("/");
  });

  it("rejects backslash and scheme tricks", () => {
    expect(sanitizeNextPath("/\\evil.example")).toBe("/");
    expect(sanitizeNextPath("\\evil.example")).toBe("/");
    expect(sanitizeNextPath("/foo://evil.example")).toBe("/");
  });

  it("defaults to / for missing or empty values", () => {
    expect(sanitizeNextPath(null)).toBe("/");
    expect(sanitizeNextPath(undefined)).toBe("/");
    expect(sanitizeNextPath("")).toBe("/");
  });
});
