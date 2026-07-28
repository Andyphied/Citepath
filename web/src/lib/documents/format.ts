/** Shorten UUID for table display (API returns uploaded_by as id only). */
export function formatUploaderId(
  uploadedBy: string,
  currentUserId?: string | null,
): string {
  if (currentUserId && uploadedBy === currentUserId) {
    return "You";
  }
  if (uploadedBy.length <= 8) {
    return uploadedBy;
  }
  return `${uploadedBy.slice(0, 8)}…`;
}

export function formatUploadedAt(iso: string): string {
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

export function formatFileType(fileType: string): string {
  return fileType ? fileType.toUpperCase() : "—";
}
