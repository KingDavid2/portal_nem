"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import client from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

/**
 * LessonPlan create/list/retrieve/delete hooks (ai-planeaciones spec —
 * "CRUD Endpoints Are Workspace-Scoped", "Generation Runs Asynchronously via
 * a Celery Task"). `/api/lesson-plans/` has no server-side `?group=` typed in
 * the generated client (the backend `get_queryset()` filter is real but
 * undocumented in the OpenAPI schema), so — mirroring `groupsForSchoolYear`/
 * `studentsForGroup` — the screen fetches every plan in the active workspace
 * and scopes it client-side via `lessonPlansForGroup`.
 *
 * `useLessonPlanQuery` polls the retrieve endpoint via `refetchInterval`
 * until `status` transitions to `ready`/`failed` (Scenario: Client polls
 * until generation completes) — `lessonPlanPollInterval` is the pure
 * resolver so the poll-until-ready/failed contract is unit-testable without
 * a live timer/network.
 */

export type LessonPlan = components["schemas"]["LessonPlan"];
export type LessonPlanStatus = LessonPlan["status"];
export type LessonPlanInput = Pick<LessonPlan, "group" | "campo" | "grade" | "theme">;

// See `schools.ts`'s `asWriteBody` comment: the backend doesn't split
// request/response schemas, so the generated request body type is the full
// `LessonPlan` including readonly response-only fields.
function asWriteBody(input: LessonPlanInput): LessonPlan {
  return input as unknown as LessonPlan;
}

export const lessonPlansQueryKey = ["lesson-plans"] as const;
export const lessonPlanQueryKey = (id: number) => ["lesson-plans", id] as const;

const POLL_INTERVAL_MS = 3000;

/** Pure helper: narrows the full workspace list down to one group's plans. */
export function lessonPlansForGroup(
  plans: LessonPlan[],
  groupId: number | null,
): LessonPlan[] {
  if (groupId === null) return [];
  return plans.filter((plan) => plan.group === groupId);
}

/** TanStack Query `refetchInterval` resolver: keep polling every
 * `POLL_INTERVAL_MS` while the plan is still loading or `pending`; stop once
 * it reaches a terminal status (`ready` or `failed`). */
export function lessonPlanPollInterval(plan: LessonPlan | undefined): number | false {
  if (!plan) return POLL_INTERVAL_MS;
  return plan.status === "pending" ? POLL_INTERVAL_MS : false;
}

export function useLessonPlansQuery() {
  return useQuery({
    queryKey: lessonPlansQueryKey,
    queryFn: async (): Promise<LessonPlan[]> => {
      const { data, error } = await client.GET("/api/lesson-plans/");
      if (error) throw new ApiError(error);
      return data ?? [];
    },
  });
}

export function useLessonPlanQuery(id: number | null) {
  return useQuery({
    queryKey: lessonPlanQueryKey(id ?? -1),
    queryFn: async (): Promise<LessonPlan> => {
      const { data, error } = await client.GET("/api/lesson-plans/{id}/", {
        params: { path: { id: id as number } },
      });
      if (error || !data) throw new ApiError(error);
      return data;
    },
    enabled: id !== null,
    refetchInterval: (query) => lessonPlanPollInterval(query.state.data),
  });
}

export function useCreateLessonPlanMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: LessonPlanInput): Promise<LessonPlan> => {
      const { data, error } = await client.POST("/api/lesson-plans/", {
        body: asWriteBody(input),
      });
      if (error || !data) throw new ApiError(error);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: lessonPlansQueryKey });
    },
  });
}

export function useDeleteLessonPlanMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number): Promise<void> => {
      const { error } = await client.DELETE("/api/lesson-plans/{id}/", {
        params: { path: { id } },
      });
      if (error) throw new ApiError(error);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: lessonPlansQueryKey });
    },
  });
}
