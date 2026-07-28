"use client";

import { useCallback, useId, useRef, useState } from "react";

const ACCEPT =
  ".md,.txt,.pdf,.json,text/markdown,text/plain,application/pdf,application/json";

export function DocumentUploadZone({
  disabled,
  uploading,
  onFileSelected,
}: {
  disabled?: boolean;
  uploading?: boolean;
  onFileSelected: (file: File) => void;
}) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const pick = useCallback(
    (file: File | undefined | null) => {
      if (!file || disabled || uploading) {
        return;
      }
      onFileSelected(file);
    },
    [disabled, uploading, onFileSelected],
  );

  return (
    <div
      className={`rounded-md border border-dashed px-4 py-6 transition-colors ${
        dragging
          ? "border-[var(--accent)] bg-[var(--accent-soft)]"
          : "border-[var(--border-strong)] bg-[var(--surface)]"
      } ${disabled || uploading ? "opacity-60" : ""}`}
      onDragEnter={(event) => {
        event.preventDefault();
        if (!disabled && !uploading) {
          setDragging(true);
        }
      }}
      onDragOver={(event) => {
        event.preventDefault();
      }}
      onDragLeave={(event) => {
        event.preventDefault();
        setDragging(false);
      }}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        const file = event.dataTransfer.files?.[0];
        pick(file);
      }}
    >
      <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-medium text-[var(--ink)]">
            {uploading ? "Uploading…" : "Upload a document"}
          </p>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Drag and drop or choose a file (.md, .txt, .pdf, .json)
          </p>
        </div>
        <div>
          <input
            ref={inputRef}
            id={inputId}
            type="file"
            accept={ACCEPT}
            className="sr-only"
            disabled={disabled || uploading}
            onChange={(event) => {
              const file = event.target.files?.[0];
              pick(file);
              event.target.value = "";
            }}
          />
          <label
            htmlFor={inputId}
            className={`inline-flex cursor-pointer rounded-md bg-[var(--accent)] px-3 py-1.5 text-sm font-medium text-white ${
              disabled || uploading
                ? "pointer-events-none cursor-not-allowed"
                : "hover:opacity-90"
            }`}
          >
            {uploading ? "Uploading…" : "Choose file"}
          </label>
        </div>
      </div>
    </div>
  );
}
