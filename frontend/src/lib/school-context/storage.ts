/**
 * Persist school / ciclo / grupo selection per workspace (non-secret UI
 * preference, same idea as active-workspace localStorage).
 */

import type { CycleSelection } from "@/lib/api/school-context-selection";
import type { Group } from "@/lib/api/groups";
import type { School } from "@/lib/api/schools";
import type { SchoolYear } from "@/lib/api/school-years";

const STORAGE_PREFIX = "portal_nem.schoolTeaching.";

export function storageKeyForWorkspace(workspaceId: string): string {
  return `${STORAGE_PREFIX}${workspaceId}`;
}

export function readStoredSelection(workspaceId: string): CycleSelection | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(storageKeyForWorkspace(workspaceId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<CycleSelection>;
    return {
      schoolId: typeof parsed.schoolId === "number" ? parsed.schoolId : null,
      schoolYearId:
        typeof parsed.schoolYearId === "number" ? parsed.schoolYearId : null,
      groupId: typeof parsed.groupId === "number" ? parsed.groupId : null,
    };
  } catch {
    return null;
  }
}

export function writeStoredSelection(
  workspaceId: string,
  selection: CycleSelection,
): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(
    storageKeyForWorkspace(workspaceId),
    JSON.stringify(selection),
  );
}

/** Drop IDs that no longer exist in the loaded workspace lists; keep cascade consistent. */
export function sanitizeSelection(
  selection: CycleSelection,
  schools: School[],
  schoolYears: SchoolYear[],
  groups: Group[],
): CycleSelection {
  let { schoolId, schoolYearId, groupId } = selection;

  if (schoolId !== null && !schools.some((s) => s.id === schoolId)) {
    return { schoolId: null, schoolYearId: null, groupId: null };
  }

  if (schoolYearId !== null) {
    const year = schoolYears.find((y) => y.id === schoolYearId);
    if (!year || (schoolId !== null && year.school !== schoolId)) {
      schoolYearId = null;
      groupId = null;
    } else if (schoolId === null) {
      schoolId = year.school;
    }
  }

  if (groupId !== null) {
    const group = groups.find((g) => g.id === groupId);
    if (!group || (schoolYearId !== null && group.school_year !== schoolYearId)) {
      groupId = null;
    } else if (schoolYearId === null) {
      schoolYearId = group.school_year;
      const year = schoolYears.find((y) => y.id === schoolYearId);
      if (year) schoolId = year.school;
    }
  }

  return { schoolId, schoolYearId, groupId };
}
