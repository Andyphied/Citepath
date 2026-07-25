import { ApiError } from "@/lib/api/client";

/** Map API / validation failures to a user-visible inline message. */
export function formatAuthError(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    if (error.code === "validation_error") {
      const details = error.details;
      const fieldMessages = Object.entries(details)
        .map(([field, value]) => {
          if (Array.isArray(value) && value.length > 0) {
            return `${field}: ${String(value[0])}`;
          }
          if (typeof value === "string") {
            return `${field}: ${value}`;
          }
          return null;
        })
        .filter((item): item is string => Boolean(item));
      if (fieldMessages.length > 0) {
        return fieldMessages.join(" · ");
      }
    }
    return error.message || fallback;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}
