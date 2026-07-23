"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import client from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

/**
 * SchoolYear CRUD hooks (frontend-foundation spec — "CRUD Screens Cover
 * School Structure Entities"). The `/api/school-years/` list endpoint has no
 * server-side `school` filter (schema.d.ts: `groups_list`/`school_years_list`
 * take no query params), so the screen fetches every school-year in the
 * active workspace and scopes it client-side via `schoolYearsForSchool`.
 */

export type SchoolYear = components["schemas"]["SchoolYear"];
export type SchoolYearInput = Pick<SchoolYear, "school" | "label">;

// See `schools.ts`'s `asWriteBody` comment: the backend doesn't split
// request/response schemas, so the generated request body type is the full
// `SchoolYear` including `readonly id`/`workspace`, which the serializer's
// `read_only_fields` ignores server-side regardless of what's sent.
function asWriteBody(input: SchoolYearInput): SchoolYear {
  return input as unknown as SchoolYear;
}

export const schoolYearsQueryKey = ["school-years"] as const;

/** Pure helper: narrows the full workspace list down to one school's years. */
export function schoolYearsForSchool(
  schoolYears: SchoolYear[],
  schoolId: number | null,
): SchoolYear[] {
  if (schoolId === null) return [];
  return schoolYears.filter((schoolYear) => schoolYear.school === schoolId);
}

export function useSchoolYearsQuery() {
  return useQuery({
    queryKey: schoolYearsQueryKey,
    queryFn: async (): Promise<SchoolYear[]> => {
      const { data, error } = await client.GET("/api/school-years/");
      if (error) throw new ApiError(error);
      return data ?? [];
    },
  });
}

export function useCreateSchoolYearMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: SchoolYearInput): Promise<SchoolYear> => {
      const { data, error } = await client.POST("/api/school-years/", {
        body: asWriteBody(input),
      });
      if (error || !data) throw new ApiError(error);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: schoolYearsQueryKey });
    },
  });
}

export function useUpdateSchoolYearMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      input,
    }: {
      id: number;
      input: SchoolYearInput;
    }): Promise<SchoolYear> => {
      const { data, error } = await client.PUT("/api/school-years/{id}/", {
        params: { path: { id } },
        body: asWriteBody(input),
      });
      if (error || !data) throw new ApiError(error);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: schoolYearsQueryKey });
    },
  });
}

export function useDeleteSchoolYearMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number): Promise<void> => {
      const { error } = await client.DELETE("/api/school-years/{id}/", {
        params: { path: { id } },
      });
      if (error) throw new ApiError(error);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: schoolYearsQueryKey });
    },
  });
}
