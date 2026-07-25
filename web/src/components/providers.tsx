"use client";

import { WorkspaceProvider } from "@/components/workspace-provider";

export function Providers({ children }: { children: React.ReactNode }) {
  return <WorkspaceProvider>{children}</WorkspaceProvider>;
}
