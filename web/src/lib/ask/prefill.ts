/** Read optional demo prefill from `?q=` (UI-004). */
export function readAskPrefill(search: string): string {
  const raw = search.startsWith("?") ? search.slice(1) : search;
  const params = new URLSearchParams(raw);
  const value = params.get("q");
  if (!value) {
    return "";
  }
  return value.trim();
}
