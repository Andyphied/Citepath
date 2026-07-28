"use client";

export type ToastTone = "success" | "error" | "info";

export function FeedbackBanner({
  tone,
  message,
  onDismiss,
}: {
  tone: ToastTone;
  message: string;
  onDismiss?: () => void;
}) {
  const styles =
    tone === "error"
      ? "border-[var(--danger-border)] bg-[var(--danger-bg)] text-[var(--danger)]"
      : tone === "success"
        ? "border-emerald-200 bg-emerald-50 text-emerald-900"
        : "border-[var(--border)] bg-[var(--surface)] text-[var(--ink)]";

  return (
    <div
      className={`flex items-start justify-between gap-3 rounded-md border px-4 py-3 text-sm ${styles}`}
      role={tone === "error" ? "alert" : "status"}
    >
      <p>{message}</p>
      {onDismiss ? (
        <button
          type="button"
          onClick={onDismiss}
          className="shrink-0 text-xs font-medium underline underline-offset-2 hover:no-underline"
        >
          Dismiss
        </button>
      ) : null}
    </div>
  );
}
