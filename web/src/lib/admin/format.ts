/** Format USD cost from API Decimal string/number for dashboard cards. */
export function formatCostUsd(value: string | number | null | undefined): string {
  const n = typeof value === "number" ? value : Number(value ?? 0);
  if (!Number.isFinite(n)) {
    return "$0.00";
  }
  if (n === 0) {
    return "$0.00";
  }
  if (n < 0.01) {
    return `$${n.toFixed(6)}`;
  }
  return `$${n.toFixed(2)}`;
}

export function formatTokenCount(value: number | null | undefined): string {
  const n = value ?? 0;
  return n.toLocaleString("en-US");
}

export function formatJobTimestamp(
  iso: string | null | undefined,
): string {
  if (!iso) {
    return "—";
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function jobStatusLabel(status: string): string {
  switch (status) {
    case "pending":
      return "Pending";
    case "processing":
      return "Processing";
    case "completed":
      return "Completed";
    case "failed":
      return "Failed";
    default:
      return status ? status.charAt(0).toUpperCase() + status.slice(1) : "—";
  }
}
