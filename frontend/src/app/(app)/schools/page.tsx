"use client";

import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/data-table";
import {
  useCreateSchoolMutation,
  useDeleteSchoolMutation,
  useSchoolsQuery,
  useUpdateSchoolMutation,
  type School,
  type SchoolInput,
} from "@/lib/api/schools";
import { SchoolForm } from "./school-form";

const LEVEL_LABELS: Record<School["level"], string> = {
  preescolar: "Preescolar",
  primaria: "Primaria",
  secundaria: "Secundaria",
};

/** School list/create/edit/delete screen (frontend-foundation spec — "CRUD
 * Screens Cover School Structure Entities", School). */
export default function SchoolsPage() {
  const schoolsQuery = useSchoolsQuery();
  const createMutation = useCreateSchoolMutation();
  const updateMutation = useUpdateSchoolMutation();
  const deleteMutation = useDeleteSchoolMutation();

  const [editingSchool, setEditingSchool] = useState<School | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [rowError, setRowError] = useState<string | null>(null);

  function handleCreate(input: SchoolInput) {
    setFormError(null);
    createMutation.mutate(input, {
      onError: (error) => setFormError(error.message),
    });
  }

  function handleUpdate(input: SchoolInput) {
    if (!editingSchool) return;
    setFormError(null);
    updateMutation.mutate(
      { id: editingSchool.id, input },
      {
        onSuccess: () => setEditingSchool(null),
        onError: (error) => setFormError(error.message),
      },
    );
  }

  function handleDelete(school: School) {
    if (!window.confirm(`¿Eliminar la escuela "${school.name}"?`)) return;
    setRowError(null);
    deleteMutation.mutate(school.id, {
      onError: (error) => setRowError(error.message),
    });
  }

  const columns = useMemo<ColumnDef<School, unknown>[]>(
    () => [
      { header: "Nombre", accessorKey: "name" },
      { header: "CCT", accessorFn: (school) => school.cct || "—" },
      { header: "Nivel", accessorFn: (school) => LEVEL_LABELS[school.level] },
      {
        id: "actions",
        header: "Acciones",
        cell: ({ row }) => (
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={() => setEditingSchool(row.original)}>
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
      <h1 className="text-xl font-semibold">Escuelas</h1>

      {editingSchool ? (
        <SchoolForm
          initial={editingSchool}
          errorMessage={formError}
          isPending={updateMutation.isPending}
          onSubmit={handleUpdate}
          onCancel={() => {
            setEditingSchool(null);
            setFormError(null);
          }}
        />
      ) : (
        <SchoolForm
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

      {schoolsQuery.isLoading ? (
        <p className="text-muted-foreground">Cargando escuelas…</p>
      ) : schoolsQuery.isError ? (
        <p className="text-sm text-destructive" role="alert">
          No se pudieron cargar las escuelas.
        </p>
      ) : (
        <DataTable columns={columns} data={schoolsQuery.data ?? []} />
      )}
    </div>
  );
}
