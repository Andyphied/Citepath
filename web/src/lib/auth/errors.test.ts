import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";
import { formatAuthError } from "@/lib/auth/errors";

describe("formatAuthError", () => {
  it("returns ApiError message for invalid credentials", () => {
    const error = new ApiError(401, "invalid_credentials", "Invalid email or password");
    expect(formatAuthError(error, "fallback")).toBe("Invalid email or password");
  });

  it("formats validation detail fields", () => {
    const error = new ApiError(422, "validation_error", "Validation failed", {
      password: ["String should have at least 8 characters"],
    });
    expect(formatAuthError(error, "fallback")).toContain("password:");
  });

  it("uses fallback for unknown values", () => {
    expect(formatAuthError(null, "Unable to sign in")).toBe("Unable to sign in");
  });
});
