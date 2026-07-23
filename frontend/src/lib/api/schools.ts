"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import client from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

/**
 * School CRUD hooks over the typed client (frontend-foundation spec — "CRUD
 * Screens Cover School Structure Entities"). Thin one-liners per design.md's
 * `orval`-rejection rationale, matching `hooks.ts`'s auth/workspace hooks.
 */

export type School = components["schemas"]["School"];
export type SchoolInput = Pick<School, "name" | "cct" | "level">;

// The backend doesn't split request/response schemas (drf-spectacular
// `COMPONENT_SPLIT_REQUEST` defaults to False), so the generated request
// body type is the full `School` — including the `readonly id`/`workspace`
// fields that `SchoolSerializer.read_only_fields` ignores server-side
// regardless of what's sent. Cast the write-only `SchoolInput` shape through
// `unknown` at the two call sites below rather than widening the public
// `SchoolInput` type with dead fields callers must never populate.
function asWriteBody(input: SchoolInput): School {
  return input as unknown as School;
}

export const schoolsQueryKey = ["schools"] as const;

export function useSchoolsQuery() {
  return useQuery({
    queryKey: schoolsQueryKey,
    queryFn: async (): Promise<School[]> => {
      const { data, error } = await client.GET("/api/schools/");
      if (error) throw new ApiError(error);
      return data ?? [];
    },
  });
}

export function useCreateSchoolMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: SchoolInput): Promise<School> => {
      const { data, error } = await client.POST("/api/schools/", {
        body: asWriteBody(input),
      });
      if (error || !data) throw new ApiError(error);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: schoolsQueryKey });
    },
  });
}

export function useUpdateSchoolMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      input,
    }: {
      id: number;
      input: SchoolInput;
    }): Promise<School> => {
      const { data, error } = await client.PUT("/api/schools/{id}/", {
        params: { path: { id } },
        body: asWriteBody(input),
      });
      if (error || !data) throw new ApiError(error);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: schoolsQueryKey });
    },
  });
}

export function useDeleteSchoolMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number): Promise<void> => {
      const { error } = await client.DELETE("/api/schools/{id}/", {
        params: { path: { id } },
      });
      if (error) throw new ApiError(error);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: schoolsQueryKey });
    },
  });
}
