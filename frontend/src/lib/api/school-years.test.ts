import { describe, expect, it } from "vitest";
import { schoolYearsForSchool, type SchoolYear } from "@/lib/api/school-years";

/**
 * Focused unit tests for the client-side school-year scoping helper
 * (frontend-foundation spec — "CRUD Screens Cover School Structure
 * Entities"; tasks.md D7 `npm test -- school`). `/api/school-years/` has no
 * server-side `school` filter, so this pure function is the real behavior
 * under test for the school-years screen.
 */
const schoolYears: SchoolYear[] = [
  { id: 1, school: 10, label: "2023-2024", workspace: "ws-1" },
  { id: 2, school: 10, label: "2024-2025", workspace: "ws-1" },
  { id: 3, school: 20, label: "2024-2025", workspace: "ws-1" },
];

describe("schoolYearsForSchool", () => {
  it("returns only school-years belonging to the given school id", () => {
    expect(schoolYearsForSchool(schoolYears, 10)).toEqual([schoolYears[0], schoolYears[1]]);
    expect(schoolYearsForSchool(schoolYears, 20)).toEqual([schoolYears[2]]);
  });

  it("returns an empty list when no school is selected", () => {
    expect(schoolYearsForSchool(schoolYears, null)).toEqual([]);
  });

  it("returns an empty list when the school id has no matching rows", () => {
    expect(schoolYearsForSchool(schoolYears, 999)).toEqual([]);
  });
});
