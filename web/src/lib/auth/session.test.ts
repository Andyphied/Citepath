import { describe, expect, it } from "vitest";

import { hasAuthCookie } from "@/lib/auth/session";
import { isProtectedPath } from "@/lib/nav";

describe("hasAuthCookie", () => {
  it("returns true when atlasops_token is present", () => {
    expect(hasAuthCookie("atlasops_token=abc123; other=1")).toBe(true);
  });

  it("returns false when cookie missing or empty", () => {
    expect(hasAuthCookie(null)).toBe(false);
    expect(hasAuthCookie("")).toBe(false);
    expect(hasAuthCookie("atlasops_token=")).toBe(false);
    expect(hasAuthCookie("session=1")).toBe(false);
  });
});

describe("isProtectedPath", () => {
  it("allows login and protects app routes", () => {
    expect(isProtectedPath("/login")).toBe(false);
    expect(isProtectedPath("/documents")).toBe(true);
    expect(isProtectedPath("/ask")).toBe(true);
    expect(isProtectedPath("/")).toBe(true);
  });
});
