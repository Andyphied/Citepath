import { getApiBaseUrl } from "@/lib/config";
import { getAccessToken } from "@/lib/auth/session";
import type { ApiErrorBody } from "@/lib/api/types";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor(
    status: number,
    code: string,
    message: string,
    details: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export type ApiFetchOptions = RequestInit & {
  /** Skip Authorization header (public endpoints). */
  skipAuth?: boolean;
  /** Override token (tests). */
  token?: string | null;
  /** Override base URL (tests). */
  baseUrl?: string;
};

async function parseError(response: Response): Promise<ApiError> {
  let code = "request_failed";
  let message = response.statusText || "Request failed";
  let details: Record<string, unknown> = {};

  try {
    const body = (await response.json()) as ApiErrorBody;
    if (body?.error) {
      code = body.error.code || code;
      message = body.error.message || message;
      details = body.error.details ?? {};
    }
  } catch {
    // Non-JSON error body — keep defaults.
  }

  return new ApiError(response.status, code, message, details);
}

/**
 * Typed fetch wrapper: JWT bearer injection + structured API errors.
 */
export async function apiFetch<T>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  const {
    skipAuth = false,
    token,
    baseUrl,
    headers: initHeaders,
    ...rest
  } = options;

  const url = `${baseUrl ?? getApiBaseUrl()}${path.startsWith("/") ? path : `/${path}`}`;
  const headers = new Headers(initHeaders);
  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }

  if (!skipAuth) {
    const accessToken = token === undefined ? getAccessToken() : token;
    if (accessToken) {
      headers.set("Authorization", `Bearer ${accessToken}`);
    }
  }

  let response: Response;
  try {
    response = await fetch(url, { ...rest, headers });
  } catch {
    throw new ApiError(
      0,
      "network_error",
      "Unable to reach the AtlasOps API. Check NEXT_PUBLIC_API_URL and that the API is running.",
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  if (!response.ok) {
    throw await parseError(response);
  }

  if (response.status === 204 || response.headers.get("content-length") === "0") {
    return undefined as T;
  }

  return (await response.json()) as T;
}
