import type { Group } from "@/lib/api/groups";
import type { SchoolYear } from "@/lib/api/school-years";

/**
 * Auto-select school / ciclo / grupo for cascading filters using the same
 * “último ciclo” rule as Quizzy MCP: max lexicographic `SchoolYear.label`.
 * Only fills a level when uniqueness makes the choice unambiguous.
 */

export type CycleSelection = {
  schoolId: number | null;
  schoolYearId: number | null;
  groupId: number | null;
};

const EMPTY: CycleSelection = {
  schoolId: null,
  schoolYearId: null,
  groupId: null,
};

/** Max lexicographic label across the given school-years, or null if empty. */
export function lastSchoolYearLabel(schoolYears: SchoolYear[]): string | null {
  if (schoolYears.length === 0) return null;
  let max = schoolYears[0]!.label;
  for (const year of schoolYears) {
    if (year.label > max) max = year.label;
  }
  return max;
}

/**
 * Resolve initial school / ciclo / grupo filters from the workspace lists.
 *
 * - Always targets the último ciclo (max label).
 * - Selects school + school-year when exactly one school has that label.
 * - Selects group when exactly one group sits on that label (deriving school
 *   and school-year from it so the cascade stays consistent).
 */
export function resolveLastCycleSelection(
  schoolYears: SchoolYear[],
  groups: Group[],
): CycleSelection {
  const lastLabel = lastSchoolYearLabel(schoolYears);
  if (lastLabel === null) return EMPTY;

  const yearsOnLast = schoolYears.filter((year) => year.label === lastLabel);
  const schoolIds = [...new Set(yearsOnLast.map((year) => year.school))];
  const yearIds = new Set(yearsOnLast.map((year) => year.id));
  const groupsOnLast = groups.filter((group) => yearIds.has(group.school_year));

  let schoolId: number | null = schoolIds.length === 1 ? schoolIds[0]! : null;
  let schoolYearId: number | null =
    schoolId === null
      ? null
      : (yearsOnLast.find((year) => year.school === schoolId)?.id ?? null);
  let groupId: number | null =
    groupsOnLast.length === 1 ? groupsOnLast[0]!.id : null;

  if (groupId !== null) {
    const group = groupsOnLast[0]!;
    const year = yearsOnLast.find((y) => y.id === group.school_year);
    if (year) {
      schoolId = year.school;
      schoolYearId = year.id;
    }
  }

  return { schoolId, schoolYearId, groupId };
}

/**
 * After the teacher picks a school, fill that school's último ciclo and — when
 * unique — its only group.
 */
export function resolveSchoolCascadeSelection(
  schoolId: number,
  schoolYears: SchoolYear[],
  groups: Group[],
): { schoolYearId: number | null; groupId: number | null } {
  const yearsForSchool = schoolYears.filter((year) => year.school === schoolId);
  const lastLabel = lastSchoolYearLabel(yearsForSchool);
  if (lastLabel === null) {
    return { schoolYearId: null, groupId: null };
  }

  const schoolYear = yearsForSchool.find((year) => year.label === lastLabel)!;
  const groupsForYear = groups.filter(
    (group) => group.school_year === schoolYear.id,
  );
  return {
    schoolYearId: schoolYear.id,
    groupId: groupsForYear.length === 1 ? groupsForYear[0]!.id : null,
  };
}
