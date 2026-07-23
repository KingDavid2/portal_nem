"use client";

import { useQuery } from "@tanstack/react-query";
import client from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

/**
 * TanStack Query hooks over the typed client (design.md "Frontend fetch
 * layer"). Kept as thin one-liners per the design's `orval` rejection
 * rationale — hooks should not grow generated/boilerplate shape.
 */

export type CurrentUser = components["schemas"]["User"];
export type Membership = components["schemas"]["MembershipList"];

export const meQueryKey = ["auth", "me"] as const;
export const workspacesQueryKey = ["workspaces"] as const;

/** Bootstraps the current session on app load (frontend-foundation spec —
 * "Session/CSRF Auth Lifecycle"). Resolves to `null` (not an error) when
 * there is no active session, since anonymous is an expected steady state. */
export function useMeQuery() {
  return useQuery({
    queryKey: meQueryKey,
    queryFn: async (): Promise<CurrentUser | null> => {
      const { data, response } = await client.GET("/api/auth/me/");
      if (response.status === 401 || response.status === 403) {
        return null;
      }
      return data ?? null;
    },
    retry: false,
  });
}

/** Lists the caller's memberships for the workspace switcher. Unscoped —
 * does not require an active workspace (design.md: workspace-list "must not
 * require `X-Workspace-Id`"). Disabled while there is no authenticated user. */
export function useWorkspacesQuery(enabled: boolean) {
  return useQuery({
    queryKey: workspacesQueryKey,
    queryFn: async (): Promise<Membership[]> => {
      const { data, error } = await client.GET("/api/workspaces/");
      if (error) {
        throw new Error("Failed to load workspaces.");
      }
      return data ?? [];
    },
    enabled,
  });
}
