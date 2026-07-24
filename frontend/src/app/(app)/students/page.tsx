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
import { SchoolContextFilters } from "@/components/school-context-filters";
import { Avatar } from "@/components/ui/avatar";

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
      { header: "Alumno", cell: ({ row }) => <div className="flex items-center gap-2"><Avatar size="sm" name={`${row.original.first_name} ${row.original.last_name_paternal}`} /><span>{row.original.first_name}</span></div> },
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

      <SchoolContextFilters
        schools={schools.map((school) => ({ id: school.id, label: school.name }))}
        schoolYears={visibleSchoolYears.map((year) => ({ id: year.id, label: year.label }))}
        groups={visibleGroups.map((group) => ({ id: group.id, label: `${group.grado}${group.grupo}` }))}
        schoolId={selectedSchoolId} schoolYearId={selectedSchoolYearId} groupId={selectedGroupId}
        onSchoolChange={(id) => { setSelectedSchoolId(id); setEditingStudent(null); setFormError(null); }}
        onSchoolYearChange={(id) => { setSelectedSchoolYearId(id); setEditingStudent(null); setFormError(null); }}
        onGroupChange={(id) => { setSelectedGroupId(id); setEditingStudent(null); setFormError(null); }}
      />

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
