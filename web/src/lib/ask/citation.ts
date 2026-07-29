/** Format optional page/section metadata for citation headers. */
export function formatCitationLocation(
  metadata: Record<string, unknown> | null | undefined,
): string | null {
  if (!metadata) {
    return null;
  }

  const parts: string[] = [];
  const page = metadata.page_number ?? metadata.page;
  if (page != null && String(page).trim() !== "") {
    parts.push(`p. ${String(page)}`);
  }

  const section =
    metadata.section_heading ?? metadata.section ?? metadata.source_type;
  if (section != null && String(section).trim() !== "") {
    parts.push(String(section));
  }

  return parts.length > 0 ? parts.join(" · ") : null;
}

export function citationDocumentTitle(
  title: string | null | undefined,
): string {
  const trimmed = title?.trim();
  return trimmed && trimmed.length > 0 ? trimmed : "Untitled document";
}
