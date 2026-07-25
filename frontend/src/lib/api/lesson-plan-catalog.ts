"use client";

import { useQuery } from "@tanstack/react-query";
import client from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

/**
 * Lesson-plan catalog read hooks (ai-planeaciones spec — "Generation Runs
 * Asynchronously via a Celery Task", the planning-form catalog contract).
 * `/api/lesson-plans/fields/` and `/api/lesson-plans/quota/` are both
 * deliberately kept separate from `/api/lesson-plans/catalog/`: the field
 * picker and the quota card render before the teacher has chosen a group or
 * a field, while `catalog` needs both to answer.
 *
 * `useLessonPlanCatalogQuery` must not fire until a group AND a field are
 * both selected — `catalogQueryEnabled` is the pure gate behind its
 * `enabled` option, kept pure so the gating contract is unit-testable
 * without a network, same reason `lessonPlanPollInterval` exists in
 * `lesson-plans.ts`.
 */

export type LessonPlanCatalog = components["schemas"]["LessonPlanCatalog"];
export type CatalogField = components["schemas"]["CatalogField"];
export type CatalogSubject = components["schemas"]["CatalogSubject"];
export type CatalogTheme = components["schemas"]["CatalogTheme"];
export type CatalogContent = components["schemas"]["CatalogContent"];
export type GenerationQuota = components["schemas"]["GenerationQuota"];

export const lessonPlanFieldsQueryKey = ["lesson-plan-fields"] as const;
export const generationQuotaQueryKey = ["generation-quota"] as const;
export const lessonPlanCatalogQueryKey = (groupId: number, fieldId: string) =>
  ["lesson-plan-catalog", groupId, fieldId] as const;

/** Pure gate for the catalog query: `GET /api/lesson-plans/catalog/` needs BOTH
 * a group and a field to answer, so the request must not fire until the teacher
 * has picked both. Kept pure so the gating contract is unit-testable without a
 * network — same reason `lessonPlanPollInterval` exists in `lesson-plans.ts`. */
export function catalogQueryEnabled(groupId: number | null, fieldId: string): boolean {
  return groupId !== null && fieldId.trim() !== "";
}

export function useLessonPlanFieldsQuery() {
  return useQuery({
    queryKey: lessonPlanFieldsQueryKey,
    queryFn: async (): Promise<CatalogField[]> => {
      const { data, error } = await client.GET("/api/lesson-plans/fields/");
      if (error) throw new ApiError(error);
      return data ?? [];
    },
  });
}

export function useGenerationQuotaQuery() {
  return useQuery({
    queryKey: generationQuotaQueryKey,
    queryFn: async (): Promise<GenerationQuota> => {
      const { data, error } = await client.GET("/api/lesson-plans/quota/");
      if (error || !data) throw new ApiError(error);
      return data;
    },
  });
}

export function useLessonPlanCatalogQuery(groupId: number | null, fieldId: string) {
  return useQuery({
    queryKey: lessonPlanCatalogQueryKey(groupId ?? -1, fieldId),
    queryFn: async (): Promise<LessonPlanCatalog> => {
      const { data, error } = await client.GET("/api/lesson-plans/catalog/", {
        params: { query: { group: groupId as number, field: fieldId } },
      });
      if (error || !data) throw new ApiError(error);
      return data;
    },
    enabled: catalogQueryEnabled(groupId, fieldId),
  });
}
