"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import client from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

/**
 * Demo-mode hooks for the guest persona picker and session polling
 * (M5 Demo mode — "provision a demo tenant via POST /api/demo/sessions/".
 *
 * `useDemoModeQuery` uses a plain fetch because `/api/health/` has no
 * typed response body in the generated schema (spectacular emits
 * "No response body"). The raw response is narrowed at runtime.
 *
 * `useDemoSessionQuery` polls the retrieve endpoint via `refetchInterval`
 * until `status` transitions to `ready`/`failed` — `demoSessionPollInterval`
 * is the pure resolver so the poll-until-ready/failed contract is
 * unit-testable without a live timer/network.
 */

export type DemoSession = components["schemas"]["DemoSession"];
export type Persona = components["schemas"]["Persona"];
export type DemoSessionStatus = DemoSession["status"];
export type PersonaEnum = components["schemas"]["PersonaEnum"];

export const demoPersonasQueryKey = ["demo", "personas"] as const;
export const demoSessionQueryKey = (id: string) => ["demo", "sessions", id] as const;

const POLL_INTERVAL_MS = 2000;

/** TanStack Query `refetchInterval` resolver: keep polling every
 * `POLL_INTERVAL_MS` while the session is still loading or `pending`; stop
 * once it reaches a terminal status (`ready` or `failed`). */
export function demoSessionPollInterval(
  session: DemoSession | undefined,
): number | false {
  if (!session) return POLL_INTERVAL_MS;
  return session.status === "pending" ? POLL_INTERVAL_MS : false;
}

function getBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

/** Narrows the untyped `/api/health/` body to the demo-mode flag. A missing,
 * null or non-boolean field means demo mode is off. */
export function readDemoModeFlag(body: unknown): boolean {
  if (typeof body !== "object" || body === null) return false;
  return (body as Record<string, unknown>).demo_mode === true;
}

export function useDemoModeQuery() {
  return useQuery({
    queryKey: ["demo", "mode"],
    queryFn: async (): Promise<boolean> => {
      const res = await fetch(`${getBaseUrl()}/api/health/`, {
        credentials: "include",
      });
      if (!res.ok) throw new ApiError({ detail: `Health check failed: ${res.status}` });
      return readDemoModeFlag(await res.json());
    },
  });
}

export function useDemoPersonasQuery() {
  return useQuery({
    queryKey: demoPersonasQueryKey,
    queryFn: async (): Promise<Persona[]> => {
      const { data, error } = await client.GET("/api/demo/personas/");
      if (error) throw new ApiError(error);
      return data ?? [];
    },
  });
}

export function useCreateDemoSessionMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (persona: PersonaEnum): Promise<DemoSession> => {
      const { data, error } = await client.POST("/api/demo/sessions/", {
        body: { persona },
      });
      if (error || !data) throw new ApiError(error);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["demo"] });
    },
  });
}

export function useDemoSessionQuery(id: string | undefined) {
  return useQuery({
    queryKey: demoSessionQueryKey(id ?? ""),
    queryFn: async (): Promise<DemoSession> => {
      const { data, error } = await client.GET("/api/demo/sessions/{id}/", {
        params: { path: { id: id as string } },
      });
      if (error || !data) throw new ApiError(error);
      return data;
    },
    enabled: !!id,
    refetchInterval: (query) => demoSessionPollInterval(query.state.data),
  });
}