"use client";

import { Header } from "@/components/header";
import { Sidebar } from "@/components/sidebar";

export function AppShell({
  title,
  children,
}: {
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-[var(--canvas)] text-[var(--ink)]">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header title={title} />
        <main className="flex-1 px-6 py-6">{children}</main>
      </div>
    </div>
  );
}
