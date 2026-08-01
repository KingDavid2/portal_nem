import { describe, expect, it } from "vitest";
import type { Group } from "@/lib/api/groups";
import type { School } from "@/lib/api/schools";
import type { SchoolYear } from "@/lib/api/school-years";
import {
  sanitizeSelection,
  storageKeyForWorkspace,
} from "@/lib/school-context/storage";

const school = (id: number): School =>
  ({
    id,
    name: `S${id}`,
    cct: null,
    level: "secundaria",
    workspace: "ws-1",
  }) as School;

const year = (id: number, schoolId: number, label: string): SchoolYear => ({
  id,
  school: schoolId,
  label,
  workspace: "ws-1",
});

const group = (id: number, schoolYear: number): Group => ({
  id,
  school_year: schoolYear,
  grado: 1,
  grupo: "A",
  workspace: "ws-1",
});

describe("storageKeyForWorkspace", () => {
  it("namespaces the key by workspace id", () => {
    expect(storageKeyForWorkspace("abc-123")).toBe(
      "portal_nem.schoolTeaching.abc-123",
    );
  });
});

describe("sanitizeSelection", () => {
  const schools = [school(10), school(20)];
  const schoolYears = [year(1, 10, "2024-2025"), year(2, 10, "2025-2026")];
  const groups = [group(100, 2), group(101, 2)];

  it("clears everything when school is missing", () => {
    expect(
      sanitizeSelection(
        { schoolId: 99, schoolYearId: 2, groupId: 100 },
        schools,
        schoolYears,
        groups,
      ),
    ).toEqual({ schoolId: null, schoolYearId: null, groupId: null });
  });

  it("clears year and group when year is missing", () => {
    expect(
      sanitizeSelection(
        { schoolId: 10, schoolYearId: 99, groupId: 100 },
        schools,
        schoolYears,
        groups,
      ),
    ).toEqual({ schoolId: 10, schoolYearId: null, groupId: null });
  });

  it("clears group when group is missing", () => {
    expect(
      sanitizeSelection(
        { schoolId: 10, schoolYearId: 2, groupId: 999 },
        schools,
        schoolYears,
        groups,
      ),
    ).toEqual({ schoolId: 10, schoolYearId: 2, groupId: null });
  });

  it("keeps a consistent valid selection", () => {
    expect(
      sanitizeSelection(
        { schoolId: 10, schoolYearId: 2, groupId: 100 },
        schools,
        schoolYears,
        groups,
      ),
    ).toEqual({ schoolId: 10, schoolYearId: 2, groupId: 100 });
  });
});
