"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import client from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";
import { generationQuotaQueryKey } from "@/lib/api/lesson-plan-catalog";

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
export type LessonPlanInput = components["schemas"]["LessonPlanCreate"];

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

/** Pure helper: rebuilds the create body of a plan from the project context
 * the backend persisted, so "regenerar" replays the original request instead
 * of a lossy approximation of it.
 *
 * Returns `null` when the plan predates the catalog contract — those rows
 * carry blank ids and null dates, and no valid create body can be derived
 * from them. Callers must offer regeneration only for a non-null result. */
export function lessonPlanCreateInput(plan: LessonPlan): LessonPlanInput | null {
  const { duration_weeks, start_date, end_date } = plan;
  if (!plan.field_id || duration_weeks === null || start_date === null) return null;
  if (end_date === null) return null;
  return {
    group: plan.group,
    field_id: plan.field_id,
    subject_id: plan.subject_id,
    methodology_id: plan.methodology_id,
    theme: plan.theme,
    context_diagnosis: plan.context_diagnosis,
    scenario: plan.scenario,
    duration_weeks,
    start_date,
    end_date,
    cross_cutting_theme_ids: [...plan.cross_cutting_theme_ids],
    content_selections: plan.content_selections.map((selection) => ({
      content_id: selection.content_id,
      pda_ids: [...selection.pda_ids],
    })),
  };
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
        body: input,
      });
      if (error || !data) throw new ApiError(error);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: lessonPlansQueryKey });
      queryClient.invalidateQueries({ queryKey: generationQuotaQueryKey });
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
