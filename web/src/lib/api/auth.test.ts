import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchCurrentUser, login, logout, register } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";

describe("auth API helpers", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("login posts credentials without Authorization and returns token payload", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          user: {
            id: "u1",
            email: "a@example.com",
            name: null,
            created_at: "2026-01-01T00:00:00Z",
          },
          access_token: "tok",
          token_type: "bearer",
          expires_in: 3600,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await login({
      email: "a@example.com",
      password: "securepass123",
    });

    expect(result.access_token).toBe("tok");
    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/auth/login");
    expect(init.method).toBe("POST");
    const headers = new Headers(init.headers);
    expect(headers.get("Authorization")).toBeNull();
    expect(JSON.parse(String(init.body))).toEqual({
      email: "a@example.com",
      password: "securepass123",
    });
  });

  it("register posts to /auth/register", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          user: {
            id: "u2",
            email: "b@example.com",
            name: null,
            created_at: "2026-01-01T00:00:00Z",
          },
          access_token: "tok2",
          token_type: "bearer",
          expires_in: 3600,
        }),
        { status: 201, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await register({ email: "b@example.com", password: "securepass123" });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/auth/register");
    expect(init.method).toBe("POST");
  });

  it("fetchCurrentUser hits /auth/me", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "u1",
          email: "a@example.com",
          name: null,
          created_at: "2026-01-01T00:00:00Z",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const user = await fetchCurrentUser("abc");
    expect(user.email).toBe("a@example.com");
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/auth/me");
    const headers = new Headers(init.headers);
    expect(headers.get("Authorization")).toBe("Bearer abc");
  });

  it("logout posts /auth/logout and tolerates 204", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(logout()).resolves.toBeUndefined();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/auth/logout");
    expect(init.method).toBe("POST");
  });

  it("surfaces structured auth errors", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "invalid_credentials",
            message: "Invalid email or password",
          },
        }),
        { status: 401, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      login({ email: "a@example.com", password: "wrongpassword" }),
    ).rejects.toMatchObject({
      name: "ApiError",
      status: 401,
      code: "invalid_credentials",
    } satisfies Partial<ApiError>);
  });
});
