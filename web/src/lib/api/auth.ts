import { apiFetch } from "@/lib/api/client";
import type { AuthTokenResponse, User } from "@/lib/api/types";

export type LoginPayload = {
  email: string;
  password: string;
};

export type RegisterPayload = {
  email: string;
  password: string;
  name?: string | null;
};

/** POST /auth/login — public. */
export function login(payload: LoginPayload): Promise<AuthTokenResponse> {
  return apiFetch<AuthTokenResponse>("/auth/login", {
    method: "POST",
    skipAuth: true,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

/** POST /auth/register — public. */
export function register(payload: RegisterPayload): Promise<AuthTokenResponse> {
  return apiFetch<AuthTokenResponse>("/auth/register", {
    method: "POST",
    skipAuth: true,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

/** GET /auth/me — bootstrap current user. */
export function fetchCurrentUser(token?: string | null): Promise<User> {
  return apiFetch<User>("/auth/me", { token });
}

/** POST /auth/logout — authenticated; MVP does not blocklist the JWT. */
export function logout(): Promise<void> {
  return apiFetch<void>("/auth/logout", { method: "POST" });
}
