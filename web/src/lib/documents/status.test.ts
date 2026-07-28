import { describe, expect, it } from "vitest";

import { canUploadDocuments } from "@/lib/api/types";
import {
  formatFileType,
  formatUploaderId,
} from "@/lib/documents/format";
import {
  anyDocumentInFlight,
  documentStatusTone,
  isDocumentInFlight,
} from "@/lib/documents/status";

describe("canUploadDocuments", () => {
  it("allows owner, admin, and member", () => {
    expect(canUploadDocuments("owner")).toBe(true);
    expect(canUploadDocuments("admin")).toBe(true);
    expect(canUploadDocuments("member")).toBe(true);
  });

  it("hides upload for viewer", () => {
    expect(canUploadDocuments("viewer")).toBe(false);
    expect(canUploadDocuments(null)).toBe(false);
  });
});

describe("document status helpers", () => {
  it("maps badge tones per UI-003 notes", () => {
    expect(documentStatusTone("uploaded")).toBe("gray");
    expect(documentStatusTone("processing")).toBe("yellow");
    expect(documentStatusTone("indexed")).toBe("green");
    expect(documentStatusTone("failed")).toBe("red");
  });

  it("detects in-flight documents for polling", () => {
    expect(isDocumentInFlight("processing")).toBe(true);
    expect(isDocumentInFlight("uploaded")).toBe(true);
    expect(isDocumentInFlight("indexed")).toBe(false);
    expect(
      anyDocumentInFlight([
        { status: "indexed" },
        { status: "processing" },
      ]),
    ).toBe(true);
  });
});

describe("document format helpers", () => {
  it("labels current user as You", () => {
    expect(formatUploaderId("abc-123", "abc-123")).toBe("You");
    expect(formatUploaderId("abcdef12-3456", "other")).toBe("abcdef12…");
  });

  it("uppercases file type", () => {
    expect(formatFileType("md")).toBe("MD");
  });
});
