import { describe, expect, it } from "vitest";
import type { Group } from "@/lib/api/groups";
import type { SchoolYear } from "@/lib/api/school-years";
import {
  lastSchoolYearLabel,
  resolveLastCycleSelection,
  resolveSchoolCascadeSelection,
} from "@/lib/api/school-context-selection";

const year = (
  id: number,
  school: number,
  label: string,
): SchoolYear => ({ id, school, label, workspace: "ws-1" });

const group = (id: number, schoolYear: number): Group => ({
  id,
  school_year: schoolYear,
  grado: 1,
  grupo: "A",
  workspace: "ws-1",
});

describe("lastSchoolYearLabel", () => {
  it("returns null for an empty list", () => {
    expect(lastSchoolYearLabel([])).toBeNull();
  });

  it("picks the max lexicographic label", () => {
    expect(
      lastSchoolYearLabel([
        year(1, 10, "2023-2024"),
        year(2, 10, "2025-2026"),
        year(3, 10, "2024-2025"),
      ]),
    ).toBe("2025-2026");
  });
});

describe("resolveLastCycleSelection", () => {
  it("returns empty when there are no school-years", () => {
    expect(resolveLastCycleSelection([], [])).toEqual({
      schoolId: null,
      schoolYearId: null,
      groupId: null,
    });
  });

  it("selects school, ciclo, and grupo when last cycle has one school and one group", () => {
    const schoolYears = [
      year(1, 10, "2023-2024"),
      year(2, 10, "2025-2026"),
    ];
    const groups = [group(100, 1), group(200, 2)];
    expect(resolveLastCycleSelection(schoolYears, groups)).toEqual({
      schoolId: 10,
      schoolYearId: 2,
      groupId: 200,
    });
  });

  it("selects school and ciclo but not grupo when last cycle has one school and many groups", () => {
    const schoolYears = [year(2, 10, "2025-2026")];
    const groups = [group(200, 2), group(201, 2)];
    expect(resolveLastCycleSelection(schoolYears, groups)).toEqual({
      schoolId: 10,
      schoolYearId: 2,
      groupId: null,
    });
  });

  it("derives school and ciclo from the unique group when many schools share last cycle", () => {
    const schoolYears = [
      year(2, 10, "2025-2026"),
      year(3, 20, "2025-2026"),
    ];
    const groups = [group(200, 2)];
    expect(resolveLastCycleSelection(schoolYears, groups)).toEqual({
      schoolId: 10,
      schoolYearId: 2,
      groupId: 200,
    });
  });

  it("leaves everything empty when many schools and many groups share last cycle", () => {
    const schoolYears = [
      year(2, 10, "2025-2026"),
      year(3, 20, "2025-2026"),
    ];
    const groups = [group(200, 2), group(300, 3)];
    expect(resolveLastCycleSelection(schoolYears, groups)).toEqual({
      schoolId: null,
      schoolYearId: null,
      groupId: null,
    });
  });

  it("ignores older-cycle groups when resolving último ciclo", () => {
    const schoolYears = [
      year(1, 10, "2023-2024"),
      year(2, 10, "2025-2026"),
    ];
    const groups = [group(100, 1), group(101, 1), group(200, 2)];
    expect(resolveLastCycleSelection(schoolYears, groups)).toEqual({
      schoolId: 10,
      schoolYearId: 2,
      groupId: 200,
    });
  });
});

describe("resolveSchoolCascadeSelection", () => {
  it("selects the school's último ciclo and its only group", () => {
    const schoolYears = [
      year(1, 10, "2023-2024"),
      year(2, 10, "2025-2026"),
      year(3, 20, "2025-2026"),
    ];
    const groups = [group(100, 1), group(200, 2), group(300, 3)];
    expect(resolveSchoolCascadeSelection(10, schoolYears, groups)).toEqual({
      schoolYearId: 2,
      groupId: 200,
    });
  });

  it("selects ciclo but not grupo when the last cycle has many groups", () => {
    const schoolYears = [year(2, 10, "2025-2026")];
    const groups = [group(200, 2), group(201, 2)];
    expect(resolveSchoolCascadeSelection(10, schoolYears, groups)).toEqual({
      schoolYearId: 2,
      groupId: null,
    });
  });

  it("returns nulls when the school has no years", () => {
    expect(resolveSchoolCascadeSelection(99, [year(2, 10, "2025-2026")], [])).toEqual({
      schoolYearId: null,
      groupId: null,
    });
  });
});
