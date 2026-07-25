import { AppShell } from "@/components/app-shell";

export function PageStub({
  title,
  storyId,
  description,
}: {
  title: string;
  storyId: string;
  description: string;
}) {
  return (
    <AppShell title={title}>
      <section className="max-w-2xl">
        <p className="text-sm uppercase tracking-[0.14em] text-[var(--muted)]">
          Coming in {storyId}
        </p>
        <h2 className="mt-2 font-[family-name:var(--font-display)] text-2xl text-[var(--ink)]">
          {title}
        </h2>
        <p className="mt-3 text-[var(--muted)] leading-relaxed">{description}</p>
      </section>
    </AppShell>
  );
}
