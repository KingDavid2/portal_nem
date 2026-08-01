"use client";

import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/data-table";
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
import { useSchoolTeachingContext } from "@/lib/school-context/school-teaching-context";

/** Student list/create/edit/delete screen, scoped to one selected School →
 * SchoolYear → Group (frontend-foundation spec — "CRUD Screens Cover School
 * Structure Entities", Student; the exit-gate walkthrough this screen
 * completes: teacher creates school → ciclo → grupo → alumno).
 * `/api/students/` returns every student in the workspace, so the picked
 * group narrows the list client-side. */
export default function StudentsPage() {
  const {
    schoolId,
    schoolYearId,
    groupId,
    setSchoolId,
    setSchoolYearId,
    setGroupId,
    schools,
    visibleSchoolYears,
    visibleGroups,
  } = useSchoolTeachingContext();
  const studentsQuery = useStudentsQuery();
  const createMutation = useCreateStudentMutation();
  const updateMutation = useUpdateStudentMutation();
  const deleteMutation = useDeleteStudentMutation();

  const [editingStudent, setEditingStudent] = useState<Student | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [rowError, setRowError] = useState<string | null>(null);

  const visibleStudents = studentsForGroup(studentsQuery.data ?? [], groupId);

  function handleSchoolChange(id: number | null) {
    setSchoolId(id);
    setEditingStudent(null);
    setFormError(null);
  }

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
        schoolId={schoolId}
        schoolYearId={schoolYearId}
        groupId={groupId}
        onSchoolChange={handleSchoolChange}
        onSchoolYearChange={(id) => {
          setSchoolYearId(id);
          setEditingStudent(null);
          setFormError(null);
        }}
        onGroupChange={(id) => {
          setGroupId(id);
          setEditingStudent(null);
          setFormError(null);
        }}
      />

      {groupId === null ? (
        <p className="text-muted-foreground">
          Selecciona una escuela, un ciclo escolar y un grupo para ver sus alumnos.
        </p>
      ) : (
        <>
          {editingStudent ? (
            <StudentForm
              groupId={groupId}
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
              groupId={groupId}
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
