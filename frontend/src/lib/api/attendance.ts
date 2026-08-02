"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import client from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

/**
 * Attendance roster read + bulk save hooks (attendance spec — Roster Read
 * Endpoint, Bulk Upsert Endpoint, Week Roster, Week Bulk). The `/asistencia`
 * screen keeps local draft state until the teacher presses Guardar asistencia.
 */

export type AttendanceStatus = components["schemas"]["Status148Enum"];
export type AttendanceRosterEntry =
  components["schemas"]["AttendanceRosterEntry"];
export type AttendanceBulkRequest =
  components["schemas"]["AttendanceBulkRequest"];
export type AttendanceWeekResponse =
  components["schemas"]["AttendanceWeekResponse"];
export type AttendanceWeekStudent =
  components["schemas"]["AttendanceWeekStudent"];
export type AttendanceWeekBulkRequest =
  components["schemas"]["AttendanceWeekBulkRequest"];

export type DraftEntry = {
  status: AttendanceStatus;
  notes: string;
};

/** Per-student map of date ISO → status for the weekly matrix draft. */
export type WeekDraft = Map<number, Record<string, AttendanceStatus>>;

export const attendanceRosterQueryKey = (
  groupId: number | null,
  date: string,
) => ["attendance", "roster", groupId, date] as const;

export const attendanceWeekQueryKey = (
  groupId: number | null,
  weekStart: string,
) => ["attendance", "week", groupId, weekStart] as const;

function pad2(n: number) {
  return String(n).padStart(2, "0");
}

export function toLocalISO(date: Date): string {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
}

export function localTodayISO(): string {
  return toLocalISO(new Date());
}

/** Monday (local) of the week containing `isoDate` (YYYY-MM-DD). */
export function mondayOf(isoDate: string): string {
  const [year, month, day] = isoDate.split("-").map(Number);
  const date = new Date(year!, month! - 1, day!);
  const weekday = date.getDay(); // 0=Sun … 6=Sat
  const offset = weekday === 0 ? -6 : 1 - weekday;
  date.setDate(date.getDate() + offset);
  return toLocalISO(date);
}

/** Mon–Fri ISO dates for a Monday `weekStart`. */
export function weekDates(weekStart: string): string[] {
  const [year, month, day] = weekStart.split("-").map(Number);
  const monday = new Date(year!, month! - 1, day!);
  return [0, 1, 2, 3, 4].map((offset) => {
    const date = new Date(monday);
    date.setDate(monday.getDate() + offset);
    return toLocalISO(date);
  });
}

export function shiftWeek(weekStart: string, weeks: number): string {
  const [year, month, day] = weekStart.split("-").map(Number);
  const date = new Date(year!, month! - 1, day!);
  date.setDate(date.getDate() + weeks * 7);
  return toLocalISO(date);
}

const MONTH_SHORT = [
  "ene",
  "feb",
  "mar",
  "abr",
  "may",
  "jun",
  "jul",
  "ago",
  "sep",
  "oct",
  "nov",
  "dic",
] as const;

const WEEKDAY_SHORT = ["Lun", "Mar", "Mié", "Jue", "Vie"] as const;

export function formatWeekRangeLabel(weekStart: string): string {
  const dates = weekDates(weekStart);
  const start = dates[0]!;
  const end = dates[4]!;
  const [, sm, sd] = start.split("-").map(Number);
  const [, em, ed] = end.split("-").map(Number);
  return `${sd} ${MONTH_SHORT[sm! - 1]} – ${ed} ${MONTH_SHORT[em! - 1]}`;
}

export function formatWeekdayHeader(isoDate: string, index: number): string {
  const day = Number(isoDate.split("-")[2]);
  return `${WEEKDAY_SHORT[index]} ${day}`;
}

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

export function weekToDraft(matrix: AttendanceWeekResponse): WeekDraft {
  return new Map(
    matrix.students.map((row) => [
      row.student,
      { ...row.days } as Record<string, AttendanceStatus>,
    ]),
  );
}

export function countAttendanceStatuses(draft: Map<number, DraftEntry>) {
  const counts = { present: 0, absent: 0, late: 0, excused: 0 };
  for (const entry of draft.values()) counts[entry.status] += 1;
  return counts;
}

export function countWeekStatuses(draft: WeekDraft) {
  const counts = { present: 0, absent: 0, late: 0, excused: 0 };
  for (const days of draft.values()) {
    for (const status of Object.values(days)) counts[status] += 1;
  }
  return counts;
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

export function useAttendanceWeekQuery(
  groupId: number | null,
  weekStart: string,
) {
  return useQuery({
    queryKey: attendanceWeekQueryKey(groupId, weekStart),
    queryFn: async (): Promise<AttendanceWeekResponse> => {
      if (groupId === null) {
        return { week_start: weekStart, dates: weekDates(weekStart), students: [] };
      }
      const { data, error } = await client.GET("/api/attendance/week/", {
        params: { query: { group: groupId, week_start: weekStart } },
      });
      if (error) throw new ApiError(error);
      return (
        data ?? {
          week_start: weekStart,
          dates: weekDates(weekStart),
          students: [],
        }
      );
    },
    enabled: groupId !== null && weekStart.length > 0,
  });
}

function invalidateAttendance(
  queryClient: ReturnType<typeof useQueryClient>,
  groupId: number,
) {
  queryClient.invalidateQueries({
    queryKey: ["attendance", "roster", groupId],
  });
  queryClient.invalidateQueries({
    queryKey: ["attendance", "week", groupId],
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
      invalidateAttendance(queryClient, variables.group);
    },
  });
}

export function useAttendanceWeekBulkMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: AttendanceWeekBulkRequest) => {
      const { data, error } = await client.PUT("/api/attendance/week/bulk/", {
        body: input,
      });
      if (error) throw new ApiError(error);
      return data;
    },
    onSuccess: (_data, variables) => {
      invalidateAttendance(queryClient, variables.group);
    },
  });
}
