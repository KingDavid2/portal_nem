"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import client from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

export type Term = components["schemas"]["Term"];
export type Activity = components["schemas"]["Activity"];
export type ActivityCreate = components["schemas"]["ActivityCreate"];
export type ActivitiesListResponse = components["schemas"]["ActivitiesListResponse"];
export type TypeEnum = components["schemas"]["TypeEnum"];
export type ScoresMatrixResponse = components["schemas"]["ScoresMatrixResponse"];
export type ScoresBulkRequest = components["schemas"]["ScoresBulkRequest"];
export type ScoresBulkResponse = components["schemas"]["ScoresBulkResponse"];

export type ActivitiesFilters = {
  field?: string;
  subject?: string;
  type?: TypeEnum;
  q?: string;
};

export const activitiesQueryKey = (
  groupId: number | null,
  termId: number | null,
  filters: ActivitiesFilters = {},
) => ["grades", "activities", groupId, termId, filters] as const;

export const scoreMatrixQueryKey = (
  groupId: number | null,
  termId: number | null,
  filters: Omit<ActivitiesFilters, "q"> = {},
) => ["grades", "scores", "matrix", groupId, termId, filters] as const;

export function activitiesQueryEnabled(groupId: number | null, termId: number | null) {
  return groupId !== null && termId !== null;
}

export function useActivitiesQuery(
  groupId: number | null,
  termId: number | null,
  filters: ActivitiesFilters = {},
) {
  return useQuery({
    queryKey: activitiesQueryKey(groupId, termId, filters),
    queryFn: async (): Promise<ActivitiesListResponse> => {
      const { data, error } = await client.GET("/api/grades/activities/", {
        params: {
          query: {
            group: groupId as number,
            term: termId as number,
            field: filters.field || undefined,
            subject: filters.subject || undefined,
            type: filters.type,
            q: filters.q || undefined,
          },
        },
      });
      if (error || !data) throw new ApiError(error);
      return data;
    },
    enabled: activitiesQueryEnabled(groupId, termId),
  });
}

export function useCreateActivityMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: ActivityCreate): Promise<Activity> => {
      const { data, error } = await client.POST("/api/grades/activities/", { body: input });
      if (error || !data) throw new ApiError(error);
      return data;
    },
    onSuccess: (_a, input) => {
      qc.invalidateQueries({ queryKey: ["grades", "activities", input.group, input.term] });
      qc.invalidateQueries({ queryKey: ["grades", "scores", "matrix", input.group, input.term] });
    },
  });
}

export function useScoreMatrixQuery(
  groupId: number | null,
  termId: number | null,
  filters: Omit<ActivitiesFilters, "q"> = {},
) {
  return useQuery({
    queryKey: scoreMatrixQueryKey(groupId, termId, filters),
    queryFn: async (): Promise<ScoresMatrixResponse> => {
      const { data, error } = await client.GET("/api/grades/scores/matrix/", {
        params: {
          query: {
            group: groupId as number,
            term: termId as number,
            field: filters.field || undefined,
            subject: filters.subject || undefined,
            type: filters.type,
          },
        },
      });
      if (error || !data) throw new ApiError(error);
      return data;
    },
    enabled: activitiesQueryEnabled(groupId, termId),
  });
}

export function useBulkUpsertScoresMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: ScoresBulkRequest): Promise<ScoresBulkResponse> => {
      const { data, error } = await client.PUT("/api/grades/scores/bulk/", { body: input });
      if (error || !data) throw new ApiError(error);
      return data;
    },
    onSuccess: (_r, input) => {
      qc.invalidateQueries({ queryKey: ["grades", "scores", "matrix", input.group] });
      qc.invalidateQueries({ queryKey: ["grades", "activities", input.group] });
    },
  });
}
