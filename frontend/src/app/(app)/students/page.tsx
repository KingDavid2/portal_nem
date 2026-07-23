"use client";

import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/data-table";
import { groupsForSchoolYear, useGroupsQuery } from "@/lib/api/groups";
import { useSchoolsQuery } from "@/lib/api/schools";
import { schoolYearsForSchool, useSchoolYearsQuery } from "@/lib/api/school-years";
import {
  studentsForGroup,
  useCreateStudentMutation,
  useDeleteStudentMutation,
  useStudentsQuery,
  useUpdateStudentMutation,
  type Student,
} from "@/lib/api/students";
import { StudentForm } from "./student-form";

/** Student list/create/edit/delete screen, scoped to one selected School →
 * SchoolYear → Group (frontend-foundation spec — "CRUD Screens Cover School
 * Structure Entities", Student; the exit-gate walkthrough this screen
 * completes: teacher creates school → ciclo → grupo → alumno).
 * `/api/students/` returns every student in the workspace, so the picked
 * group narrows the list client-side. */
export default function StudentsPage() {
  const schoolsQuery = useSchoolsQuery();
  const schoolYearsQuery = useSchoolYearsQuery();
  const groupsQuery = useGroupsQuery();
  const studentsQuery = useStudentsQuery();
  const createMutation = useCreateStudentMutation();
  const updateMutation = useUpdateStudentMutation();
  const deleteMutation = useDeleteStudentMutation();

  const [selectedSchoolId, setSelectedSchoolId] = useState<number | null>(null);
  const [selectedSchoolYearId, setSelectedSchoolYearId] = useState<number | null>(null);
  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null);
  const [editingStudent, setEditingStudent] = useState<Student | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [rowError, setRowError] = useState<string | null>(null);

  const schools = schoolsQuery.data ?? [];
  const visibleSchoolYears = schoolYearsForSchool(
    schoolYearsQuery.data ?? [],
    selectedSchoolId,
  );
  const visibleGroups = groupsForSchoolYear(groupsQuery.data ?? [], selectedSchoolYearId);
  const visibleStudents = studentsForGroup(studentsQuery.data ?? [], selectedGroupId);

  function handleCreate(input: {
    group: number;
    first_name: string;
    last_name_paternal: string;
    last_name_maternal: string;
    curp: string;
  }) {
    setFormError(null);
    createMutation.mutate(input, {
      onError: (error) => setFormError(error.message),
    });
  }

  function handleUpdate(input: {
    group: number;
    first_name: string;
    last_name_paternal: string;
    last_name_maternal: string;
    curp: string;
  }) {
    if (!editingStudent) return;
    setFormError(null);
    updateMutation.mutate(
      { id: editingStudent.id, input },
      {
        onSuccess: () => setEditingStudent(null),
        onError: (error) => setFormError(error.message),
      },
    );
  }

  function handleDelete(student: Student) {
    if (
      !window.confirm(
        `¿Eliminar al alumno "${student.first_name} ${student.last_name_paternal}"?`,
      )
    )
      return;
    setRowError(null);
    deleteMutation.mutate(student.id, {
      onError: (error) => setRowError(error.message),
    });
  }

  const columns = useMemo<ColumnDef<Student, unknown>[]>(
    () => [
      { header: "Nombre(s)", accessorKey: "first_name" },
      { header: "Apellido paterno", accessorKey: "last_name_paternal" },
      { header: "Apellido materno", accessorFn: (student) => student.last_name_maternal || "—" },
      { header: "CURP", accessorFn: (student) => student.curp || "—" },
      {
        id: "actions",
        header: "Acciones",
        cell: ({ row }) => (
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={() => setEditingStudent(row.original)}>
              Editar
            </Button>
            <Button size="sm" variant="destructive" onClick={() => handleDelete(row.original)}>
              Eliminar
            </Button>
          </div>
        ),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold">Alumnos</h1>

      <div className="flex flex-wrap gap-4">
        <label className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">Escuela</span>
          <select
            className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm"
            value={selectedSchoolId ?? ""}
            onChange={(event) => {
              setSelectedSchoolId(event.target.value ? Number(event.target.value) : null);
              setSelectedSchoolYearId(null);
              setSelectedGroupId(null);
              setEditingStudent(null);
              setFormError(null);
            }}
          >
            <option value="">Selecciona una escuela…</option>
            {schools.map((school) => (
              <option key={school.id} value={school.id}>
                {school.name}
              </option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">Ciclo escolar</span>
          <select
            className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm"
            value={selectedSchoolYearId ?? ""}
            disabled={selectedSchoolId === null}
            onChange={(event) => {
              setSelectedSchoolYearId(event.target.value ? Number(event.target.value) : null);
              setSelectedGroupId(null);
              setEditingStudent(null);
              setFormError(null);
            }}
          >
            <option value="">Selecciona un ciclo escolar…</option>
            {visibleSchoolYears.map((schoolYear) => (
              <option key={schoolYear.id} value={schoolYear.id}>
                {schoolYear.label}
              </option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">Grupo</span>
          <select
            className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm"
            value={selectedGroupId ?? ""}
            disabled={selectedSchoolYearId === null}
            onChange={(event) => {
              setSelectedGroupId(event.target.value ? Number(event.target.value) : null);
              setEditingStudent(null);
              setFormError(null);
            }}
          >
            <option value="">Selecciona un grupo…</option>
            {visibleGroups.map((group) => (
              <option key={group.id} value={group.id}>
                {group.grado}
                {group.grupo}
              </option>
            ))}
          </select>
        </label>
      </div>

      {selectedGroupId === null ? (
        <p className="text-muted-foreground">
          Selecciona una escuela, un ciclo escolar y un grupo para ver sus alumnos.
        </p>
      ) : (
        <>
          {editingStudent ? (
            <StudentForm
              groupId={selectedGroupId}
              initial={editingStudent}
              errorMessage={formError}
              isPending={updateMutation.isPending}
              onSubmit={handleUpdate}
              onCancel={() => {
                setEditingStudent(null);
                setFormError(null);
              }}
            />
          ) : (
            <StudentForm
              groupId={selectedGroupId}
              errorMessage={formError}
              isPending={createMutation.isPending}
              onSubmit={handleCreate}
            />
          )}

          {rowError ? (
            <p className="text-sm text-destructive" role="alert">
              {rowError}
            </p>
          ) : null}

          {studentsQuery.isLoading ? (
            <p className="text-muted-foreground">Cargando alumnos…</p>
          ) : studentsQuery.isError ? (
            <p className="text-sm text-destructive" role="alert">
              No se pudieron cargar los alumnos.
            </p>
          ) : (
            <DataTable columns={columns} data={visibleStudents} />
          )}
        </>
      )}
    </div>
  );
}
