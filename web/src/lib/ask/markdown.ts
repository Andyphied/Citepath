/**
 * Lightweight markdown → safe HTML for RAG answers.
 * Escapes raw HTML first, then applies a small subset of markdown.
 */

export function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatInline(escaped: string): string {
  let out = escaped;
  out = out.replace(/`([^`]+)`/g, "<code>$1</code>");
  out = out.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  out = out.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  return out;
}

function isUnorderedItem(line: string): boolean {
  return /^[-*]\s+/.test(line);
}

function isOrderedItem(line: string): boolean {
  return /^\d+\.\s+/.test(line);
}

/**
 * Convert a constrained markdown subset to escaped HTML.
 * Supports paragraphs, headings, bold/italic/code, and lists.
 */
export function markdownToSafeHtml(markdown: string): string {
  const normalized = markdown.replace(/\r\n/g, "\n").trim();
  if (!normalized) {
    return "";
  }

  const lines = normalized.split("\n");
  const blocks: string[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i] ?? "";
    if (line.trim() === "") {
      i += 1;
      continue;
    }

    const heading = /^(#{1,3})\s+(.+)$/.exec(line);
    if (heading) {
      const level = heading[1].length;
      blocks.push(
        `<h${level}>${formatInline(escapeHtml(heading[2].trim()))}</h${level}>`,
      );
      i += 1;
      continue;
    }

    if (isUnorderedItem(line)) {
      const items: string[] = [];
      while (i < lines.length && isUnorderedItem(lines[i] ?? "")) {
        const text = (lines[i] ?? "").replace(/^[-*]\s+/, "");
        items.push(`<li>${formatInline(escapeHtml(text))}</li>`);
        i += 1;
      }
      blocks.push(`<ul>${items.join("")}</ul>`);
      continue;
    }

    if (isOrderedItem(line)) {
      const items: string[] = [];
      while (i < lines.length && isOrderedItem(lines[i] ?? "")) {
        const text = (lines[i] ?? "").replace(/^\d+\.\s+/, "");
        items.push(`<li>${formatInline(escapeHtml(text))}</li>`);
        i += 1;
      }
      blocks.push(`<ol>${items.join("")}</ol>`);
      continue;
    }

    const para: string[] = [];
    while (
      i < lines.length &&
      (lines[i] ?? "").trim() !== "" &&
      !/^(#{1,3})\s+/.test(lines[i] ?? "") &&
      !isUnorderedItem(lines[i] ?? "") &&
      !isOrderedItem(lines[i] ?? "")
    ) {
      para.push((lines[i] ?? "").trim());
      i += 1;
    }
    blocks.push(`<p>${formatInline(escapeHtml(para.join(" ")))}</p>`);
  }

  return blocks.join("");
}
