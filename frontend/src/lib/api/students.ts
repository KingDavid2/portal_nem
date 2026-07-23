"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import client from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

/**
 * Student CRUD hooks (frontend-foundation spec — "CRUD Screens Cover School
 * Structure Entities", Student). `/api/students/` has no server-side
 * `group` filter, so the screen fetches every student in the active
 * workspace and scopes it client-side via `studentsForGroup`.
 */

export type Student = components["schemas"]["Student"];
export type StudentInput = Pick<
  Student,
  "group" | "first_name" | "last_name_paternal" | "last_name_maternal" | "curp"
>;

// See `schools.ts`'s `asWriteBody` comment: the backend doesn't split
// request/response schemas, so the generated request body type is the full
// `Student` including `readonly id`/`workspace`.
function asWriteBody(input: StudentInput): Student {
  return input as unknown as Student;
}

export const studentsQueryKey = ["students"] as const;

/** Pure helper: narrows the full workspace list down to one group's students. */
export function studentsForGroup(
  students: Student[],
  groupId: number | null,
): Student[] {
  if (groupId === null) return [];
  return students.filter((student) => student.group === groupId);
}

export function useStudentsQuery() {
  return useQuery({
    queryKey: studentsQueryKey,
    queryFn: async (): Promise<Student[]> => {
      const { data, error } = await client.GET("/api/students/");
      if (error) throw new ApiError(error);
      return data ?? [];
    },
  });
}

export function useCreateStudentMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: StudentInput): Promise<Student> => {
      const { data, error } = await client.POST("/api/students/", {
        body: asWriteBody(input),
      });
      if (error || !data) throw new ApiError(error);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: studentsQueryKey });
    },
  });
}

export function useUpdateStudentMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      input,
    }: {
      id: number;
      input: StudentInput;
    }): Promise<Student> => {
      const { data, error } = await client.PUT("/api/students/{id}/", {
        params: { path: { id } },
        body: asWriteBody(input),
      });
      if (error || !data) throw new ApiError(error);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: studentsQueryKey });
    },
  });
}

export function useDeleteStudentMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number): Promise<void> => {
      const { error } = await client.DELETE("/api/students/{id}/", {
        params: { path: { id } },
      });
      if (error) throw new ApiError(error);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: studentsQueryKey });
    },
  });
}
