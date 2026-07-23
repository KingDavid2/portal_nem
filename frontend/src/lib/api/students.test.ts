import { describe, expect, it } from "vitest";
import { studentsForGroup, type Student } from "@/lib/api/students";

/**
 * Focused unit tests for the client-side student scoping helper
 * (frontend-foundation spec — "CRUD Screens Cover School Structure
 * Entities"; tasks.md D8 `npm test -- group student`). `/api/students/` has
 * no server-side `group` filter, so this pure function is the real behavior
 * under test for the students screen.
 */
const students: Student[] = [
  {
    id: 1,
    group: 10,
    first_name: "Ana",
    last_name_paternal: "López",
    last_name_maternal: "",
    curp: "",
    workspace: "ws-1",
  },
  {
    id: 2,
    group: 10,
    first_name: "Beto",
    last_name_paternal: "García",
    last_name_maternal: "Ruiz",
    curp: "",
    workspace: "ws-1",
  },
  {
    id: 3,
    group: 20,
    first_name: "Carla",
    last_name_paternal: "Pérez",
    last_name_maternal: "",
    curp: "",
    workspace: "ws-1",
  },
];

describe("studentsForGroup", () => {
  it("returns only students belonging to the given group id", () => {
    expect(studentsForGroup(students, 10)).toEqual([students[0], students[1]]);
    expect(studentsForGroup(students, 20)).toEqual([students[2]]);
  });

  it("returns an empty list when no group is selected", () => {
    expect(studentsForGroup(students, null)).toEqual([]);
  });

  it("returns an empty list when the group id has no matching rows", () => {
    expect(studentsForGroup(students, 999)).toEqual([]);
  });
});
