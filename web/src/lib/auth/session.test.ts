import { afterEach, describe, expect, it } from "vitest";

import {
  clearAccessToken,
  getAccessToken,
  hasAuthCookie,
  setAccessToken,
} from "@/lib/auth/session";
import { isProtectedPath } from "@/lib/nav";

describe("hasAuthCookie", () => {
  it("returns true when citepath_token is present", () => {
    expect(hasAuthCookie("citepath_token=abc123; other=1")).toBe(true);
  });

  it("returns false when cookie missing or empty", () => {
    expect(hasAuthCookie(null)).toBe(false);
    expect(hasAuthCookie("")).toBe(false);
    expect(hasAuthCookie("citepath_token=")).toBe(false);
    expect(hasAuthCookie("session=1")).toBe(false);
  });
});

describe("isProtectedPath", () => {
  it("allows auth routes and protects app routes", () => {
    expect(isProtectedPath("/login")).toBe(false);
    expect(isProtectedPath("/register")).toBe(false);
    expect(isProtectedPath("/documents")).toBe(true);
    expect(isProtectedPath("/ask")).toBe(true);
    expect(isProtectedPath("/")).toBe(true);
  });
});

describe("session cookie helpers", () => {
  afterEach(() => {
    clearAccessToken();
  });

  it("sets and clears the access token cookie", () => {
    setAccessToken("jwt-value");
    expect(getAccessToken()).toBe("jwt-value");
    expect(document.cookie).toContain("citepath_token=");

    clearAccessToken();
    expect(getAccessToken()).toBeNull();
  });
});
