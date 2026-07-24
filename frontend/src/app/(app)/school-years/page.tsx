"use client";

import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/data-table";
import { useSchoolsQuery } from "@/lib/api/schools";
import {
  schoolYearsForSchool,
  useCreateSchoolYearMutation,
  useDeleteSchoolYearMutation,
  useSchoolYearsQuery,
  useUpdateSchoolYearMutation,
  type SchoolYear,
} from "@/lib/api/school-years";
import { SchoolYearForm } from "./school-year-form";
import { Card } from "@/components/ui/card";

/** SchoolYear list/create/edit/delete screen, scoped to one selected School
 * (frontend-foundation spec — "CRUD Screens Cover School Structure
 * Entities", SchoolYear). `/api/school-years/` returns every school-year in
 * the workspace, so the picked school narrows the list client-side. */
export default function SchoolYearsPage() {
  const schoolsQuery = useSchoolsQuery();
  const schoolYearsQuery = useSchoolYearsQuery();
  const createMutation = useCreateSchoolYearMutation();
  const updateMutation = useUpdateSchoolYearMutation();
  const deleteMutation = useDeleteSchoolYearMutation();

  const [selectedSchoolId, setSelectedSchoolId] = useState<number | null>(null);
  const [editingSchoolYear, setEditingSchoolYear] = useState<SchoolYear | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [rowError, setRowError] = useState<string | null>(null);

  const schools = schoolsQuery.data ?? [];
  const visibleSchoolYears = schoolYearsForSchool(
    schoolYearsQuery.data ?? [],
    selectedSchoolId,
  );

  function handleCreate(input: { school: number; label: string }) {
    setFormError(null);
    createMutation.mutate(input, {
      onError: (error) => setFormError(error.message),
    });
  }

  function handleUpdate(input: { school: number; label: string }) {
    if (!editingSchoolYear) return;
    setFormError(null);
    updateMutation.mutate(
      { id: editingSchoolYear.id, input },
      {
        onSuccess: () => setEditingSchoolYear(null),
        onError: (error) => setFormError(error.message),
      },
    );
  }

  function handleDelete(schoolYear: SchoolYear) {
    if (!window.confirm(`¿Eliminar el ciclo escolar "${schoolYear.label}"?`)) return;
    setRowError(null);
    deleteMutation.mutate(schoolYear.id, {
      onError: (error) => setRowError(error.message),
    });
  }

  const columns = useMemo<ColumnDef<SchoolYear, unknown>[]>(
    () => [
      { header: "Etiqueta", accessorKey: "label" },
      {
        id: "actions",
        header: "Acciones",
        cell: ({ row }) => (
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={() => setEditingSchoolYear(row.original)}>
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
      <h1 className="text-xl font-semibold">Ciclos escolares</h1>

      <label className="flex items-center gap-2 text-sm">
        <span className="text-muted-foreground">Escuela</span>
        <select
          className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm"
          value={selectedSchoolId ?? ""}
          onChange={(event) => {
            setSelectedSchoolId(event.target.value ? Number(event.target.value) : null);
            setEditingSchoolYear(null);
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

      {selectedSchoolId === null ? (
        <p className="text-muted-foreground">Selecciona una escuela para ver sus ciclos escolares.</p>
      ) : (
        <>
          {editingSchoolYear ? (
            <SchoolYearForm
              schoolId={selectedSchoolId}
              initial={editingSchoolYear}
              errorMessage={formError}
              isPending={updateMutation.isPending}
              onSubmit={handleUpdate}
              onCancel={() => {
                setEditingSchoolYear(null);
                setFormError(null);
              }}
            />
          ) : (
            <SchoolYearForm
              schoolId={selectedSchoolId}
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

          {schoolYearsQuery.isLoading ? (
            <p className="text-muted-foreground">Cargando ciclos escolares…</p>
          ) : schoolYearsQuery.isError ? (
            <p className="text-sm text-destructive" role="alert">
              No se pudieron cargar los ciclos escolares.
            </p>
          ) : (
            <Card className="p-0"><DataTable columns={columns} data={visibleSchoolYears} /></Card>
          )}
        </>
      )}
    </div>
  );
}
