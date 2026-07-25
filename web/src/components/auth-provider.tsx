"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { fetchCurrentUser, logout as logoutRequest } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";
import type { User } from "@/lib/api/types";
import {
  clearAccessToken,
  getAccessToken,
  setAccessToken,
} from "@/lib/auth/session";

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  /** Persist token and optionally seed user from login/register response. */
  establishSession: (token: string, user?: User) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setUser(null);
      setError(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const profile = await fetchCurrentUser(token);
      setUser(profile);
    } catch (err) {
      clearAccessToken();
      setUser(null);
      if (err instanceof ApiError && err.status === 401) {
        setError(null);
      } else {
        setError(
          err instanceof ApiError
            ? err.message
            : "Failed to load your session.",
        );
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const establishSession = useCallback(
    async (token: string, seededUser?: User) => {
      setAccessToken(token);
      if (seededUser) {
        setUser(seededUser);
        setError(null);
        setLoading(false);
        return;
      }
      await refresh();
    },
    [refresh],
  );

  const logout = useCallback(async () => {
    try {
      await logoutRequest();
    } catch {
      // Client discard is authoritative for MVP (no server blocklist).
    } finally {
      clearAccessToken();
      setUser(null);
      setError(null);
      setLoading(false);
    }
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      error,
      refresh,
      establishSession,
      logout,
    }),
    [user, loading, error, refresh, establishSession, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
