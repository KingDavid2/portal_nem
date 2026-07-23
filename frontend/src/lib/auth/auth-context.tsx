"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import client from "@/lib/api/client";
import { meQueryKey, useMeQuery, type CurrentUser } from "@/lib/api/hooks";
import { setActiveWorkspaceId } from "@/lib/workspace/store";

/**
 * Session/CSRF auth lifecycle (frontend-foundation spec — "Session/CSRF Auth
 * Lifecycle"): bootstraps via `GET /api/auth/me/` on app load, exposes
 * `login`/`logout` calling the real endpoints, and holds the current user.
 * No JWT and no token in localStorage — only the httpOnly session cookie and
 * the CSRF-echo cookie the fetch layer already handles.
 */

interface AuthContextValue {
  user: CurrentUser | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<CurrentUser>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const meQuery = useMeQuery();

  const login = useCallback(
    async (email: string, password: string): Promise<CurrentUser> => {
      const { data, error } = await client.POST("/api/auth/login/", {
        body: { email, password },
      });
      if (error || !data) {
        throw new Error("Invalid email or password.");
      }
      queryClient.setQueryData(meQueryKey, data);
      return data;
    },
    [queryClient],
  );

  const logout = useCallback(async (): Promise<void> => {
    await client.POST("/api/auth/logout/");
    queryClient.setQueryData(meQueryKey, null);
    // Clear cached data-request results (schools/groups/students/etc.) — they
    // were scoped to a session + workspace that no longer applies.
    queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== "auth" });
    setActiveWorkspaceId(null);
  }, [queryClient]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user: meQuery.data ?? null,
      isLoading: meQuery.isLoading,
      login,
      logout,
    }),
    [meQuery.data, meQuery.isLoading, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
