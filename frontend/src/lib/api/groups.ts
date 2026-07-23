"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import client from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

/**
 * Group CRUD hooks (frontend-foundation spec — "CRUD Screens Cover School
 * Structure Entities", Group). `/api/groups/` has no server-side
 * `school_year` filter, so the screen fetches every group in the active
 * workspace and scopes it client-side via `groupsForSchoolYear`. Deleting a
 * group with students triggers the backend's `PROTECT` 4xx
 * (`schools/viewsets.py` `GroupViewSet.perform_destroy`); callers surface
 * that via the shared `ApiError`/`extractErrorMessage` path, same as any
 * other write error.
 */

export type Group = components["schemas"]["Group"];
export type GroupInput = Pick<Group, "school_year" | "grado" | "grupo">;

// See `schools.ts`'s `asWriteBody` comment: the backend doesn't split
// request/response schemas, so the generated request body type is the full
// `Group` including `readonly id`/`workspace`.
function asWriteBody(input: GroupInput): Group {
  return input as unknown as Group;
}

export const groupsQueryKey = ["groups"] as const;

/** Pure helper: narrows the full workspace list down to one school-year's groups. */
export function groupsForSchoolYear(
  groups: Group[],
  schoolYearId: number | null,
): Group[] {
  if (schoolYearId === null) return [];
  return groups.filter((group) => group.school_year === schoolYearId);
}

export function useGroupsQuery() {
  return useQuery({
    queryKey: groupsQueryKey,
    queryFn: async (): Promise<Group[]> => {
      const { data, error } = await client.GET("/api/groups/");
      if (error) throw new ApiError(error);
      return data ?? [];
    },
  });
}

export function useCreateGroupMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: GroupInput): Promise<Group> => {
      const { data, error } = await client.POST("/api/groups/", {
        body: asWriteBody(input),
      });
      if (error || !data) throw new ApiError(error);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: groupsQueryKey });
    },
  });
}

export function useUpdateGroupMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      input,
    }: {
      id: number;
      input: GroupInput;
    }): Promise<Group> => {
      const { data, error } = await client.PUT("/api/groups/{id}/", {
        params: { path: { id } },
        body: asWriteBody(input),
      });
      if (error || !data) throw new ApiError(error);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: groupsQueryKey });
    },
  });
}

export function useDeleteGroupMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number): Promise<void> => {
      const { error } = await client.DELETE("/api/groups/{id}/", {
        params: { path: { id } },
      });
      if (error) throw new ApiError(error);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: groupsQueryKey });
    },
  });
}
