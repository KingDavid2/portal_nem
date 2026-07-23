import { describe, expect, it } from "vitest";
import { groupsForSchoolYear, type Group } from "@/lib/api/groups";

/**
 * Focused unit tests for the client-side group scoping helper
 * (frontend-foundation spec — "CRUD Screens Cover School Structure
 * Entities"; tasks.md D8 `npm test -- group student`). `/api/groups/` has
 * no server-side `school_year` filter, so this pure function is the real
 * behavior under test for the groups screen.
 */
const groups: Group[] = [
  { id: 1, school_year: 100, grado: 1, grupo: "A", workspace: "ws-1" },
  { id: 2, school_year: 100, grado: 2, grupo: "B", workspace: "ws-1" },
  { id: 3, school_year: 200, grado: 1, grupo: "A", workspace: "ws-1" },
];

describe("groupsForSchoolYear", () => {
  it("returns only groups belonging to the given school-year id", () => {
    expect(groupsForSchoolYear(groups, 100)).toEqual([groups[0], groups[1]]);
    expect(groupsForSchoolYear(groups, 200)).toEqual([groups[2]]);
  });

  it("returns an empty list when no school-year is selected", () => {
    expect(groupsForSchoolYear(groups, null)).toEqual([]);
  });

  it("returns an empty list when the school-year id has no matching rows", () => {
    expect(groupsForSchoolYear(groups, 999)).toEqual([]);
  });
});
