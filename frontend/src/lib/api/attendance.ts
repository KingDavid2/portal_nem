"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import client from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

/**
 * Attendance roster read + bulk save hooks (attendance spec — Roster Read
 * Endpoint, Bulk Upsert Endpoint). The `/asistencia` screen keeps local draft
 * state until the teacher presses Guardar asistencia.
 */

export type AttendanceStatus = components["schemas"]["Status148Enum"];
export type AttendanceRosterEntry =
  components["schemas"]["AttendanceRosterEntry"];
export type AttendanceBulkRequest =
  components["schemas"]["AttendanceBulkRequest"];

export type DraftEntry = {
  status: AttendanceStatus;
  notes: string;
};

export const attendanceRosterQueryKey = (
  groupId: number | null,
  date: string,
) => ["attendance", "roster", groupId, date] as const;

export function rosterToDraft(
  roster: AttendanceRosterEntry[],
): Map<number, DraftEntry> {
  return new Map(
    roster.map((row) => [
      row.student,
      { status: row.status, notes: row.notes },
    ]),
  );
}

export function countAttendanceStatuses(draft: Map<number, DraftEntry>) {
  const counts = { present: 0, absent: 0, late: 0, excused: 0 };
  for (const entry of draft.values()) counts[entry.status] += 1;
  return counts;
}

export function localTodayISO(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function useAttendanceRosterQuery(
  groupId: number | null,
  date: string,
) {
  return useQuery({
    queryKey: attendanceRosterQueryKey(groupId, date),
    queryFn: async (): Promise<AttendanceRosterEntry[]> => {
      if (groupId === null) return [];
      const { data, error } = await client.GET("/api/attendance/roster/", {
        params: { query: { group: groupId, date } },
      });
      if (error) throw new ApiError(error);
      return data ?? [];
    },
    enabled: groupId !== null && date.length > 0,
  });
}

export function useAttendanceBulkMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: AttendanceBulkRequest) => {
      const { data, error } = await client.PUT("/api/attendance/bulk/", {
        body: input,
      });
      if (error) throw new ApiError(error);
      return data;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: attendanceRosterQueryKey(variables.group, variables.date),
      });
    },
  });
}
