"use client";

import { markdownToSafeHtml } from "@/lib/ask/markdown";

export function MarkdownAnswer({ text }: { text: string }) {
  const html = markdownToSafeHtml(text);
  if (!html) {
    return null;
  }
  return (
    <div
      className="ask-markdown text-sm leading-relaxed text-[var(--ink)] [&_code]:rounded [&_code]:bg-[var(--accent-soft)] [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-[family-name:var(--font-mono)] [&_code]:text-[0.85em] [&_em]:italic [&_h1]:mb-2 [&_h1]:font-[family-name:var(--font-display)] [&_h1]:text-xl [&_h2]:mb-2 [&_h2]:font-[family-name:var(--font-display)] [&_h2]:text-lg [&_h3]:mb-1.5 [&_h3]:font-[family-name:var(--font-display)] [&_h3]:text-base [&_li]:my-0.5 [&_ol]:my-2 [&_ol]:list-decimal [&_ol]:pl-5 [&_p+p]:mt-2 [&_strong]:font-semibold [&_ul]:my-2 [&_ul]:list-disc [&_ul]:pl-5"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
