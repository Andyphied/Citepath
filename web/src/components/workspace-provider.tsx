"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { ApiError } from "@/lib/api/client";
import { listWorkspaces } from "@/lib/api/workspaces";
import type { WorkspaceListItem } from "@/lib/api/types";
import { isAuthenticated } from "@/lib/auth/session";
import {
  getStoredActiveWorkspaceId,
  resolveActiveWorkspaceId,
  setStoredActiveWorkspaceId,
  workspaceApiPath,
} from "@/lib/workspace/storage";

type WorkspaceContextValue = {
  workspaces: WorkspaceListItem[];
  activeWorkspaceId: string | null;
  activeWorkspace: WorkspaceListItem | null;
  loading: boolean;
  error: string | null;
  setActiveWorkspaceId: (workspaceId: string) => void;
  refresh: () => Promise<void>;
  /** Path helper so subsequent API calls use the selected workspace (WS-006). */
  workspacePath: (suffix?: string) => string | null;
};

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [workspaces, setWorkspaces] = useState<WorkspaceListItem[]>([]);
  const [activeWorkspaceId, setActiveId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!isAuthenticated()) {
      setWorkspaces([]);
      setActiveId(null);
      setLoading(false);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await listWorkspaces();
      const items = response.items ?? [];
      setWorkspaces(items);
      const nextId = resolveActiveWorkspaceId(
        items.map((item) => item.id),
        getStoredActiveWorkspaceId(),
      );
      setActiveId(nextId);
      if (nextId) {
        setStoredActiveWorkspaceId(nextId);
      }
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "Failed to load workspaces.";
      setError(message);
      setWorkspaces([]);
      setActiveId(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const setActiveWorkspaceId = useCallback((workspaceId: string) => {
    setActiveId(workspaceId);
    setStoredActiveWorkspaceId(workspaceId);
  }, []);

  const activeWorkspace = useMemo(
    () => workspaces.find((item) => item.id === activeWorkspaceId) ?? null,
    [workspaces, activeWorkspaceId],
  );

  const workspacePath = useCallback(
    (suffix = "") => {
      if (!activeWorkspaceId) {
        return null;
      }
      return workspaceApiPath(activeWorkspaceId, suffix);
    },
    [activeWorkspaceId],
  );

  const value = useMemo(
    () => ({
      workspaces,
      activeWorkspaceId,
      activeWorkspace,
      loading,
      error,
      setActiveWorkspaceId,
      refresh,
      workspacePath,
    }),
    [
      workspaces,
      activeWorkspaceId,
      activeWorkspace,
      loading,
      error,
      setActiveWorkspaceId,
      refresh,
      workspacePath,
    ],
  );

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace(): WorkspaceContextValue {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) {
    throw new Error("useWorkspace must be used within WorkspaceProvider");
  }
  return ctx;
}
