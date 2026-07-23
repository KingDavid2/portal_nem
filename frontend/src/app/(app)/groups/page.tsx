"use client";

import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/data-table";
import {
  useCreateGroupMutation,
  useDeleteGroupMutation,
  useGroupsQuery,
  useUpdateGroupMutation,
  groupsForSchoolYear,
  type Group,
} from "@/lib/api/groups";
import { useSchoolsQuery } from "@/lib/api/schools";
import { schoolYearsForSchool, useSchoolYearsQuery } from "@/lib/api/school-years";
import { GroupForm } from "./group-form";

/** Group list/create/edit/delete screen, scoped to one selected School →
 * SchoolYear (frontend-foundation spec — "CRUD Screens Cover School
 * Structure Entities", Group). `/api/groups/` returns every group in the
 * workspace, so the picked school-year narrows the list client-side. */
export default function GroupsPage() {
  const schoolsQuery = useSchoolsQuery();
  const schoolYearsQuery = useSchoolYearsQuery();
  const groupsQuery = useGroupsQuery();
  const createMutation = useCreateGroupMutation();
  const updateMutation = useUpdateGroupMutation();
  const deleteMutation = useDeleteGroupMutation();

  const [selectedSchoolId, setSelectedSchoolId] = useState<number | null>(null);
  const [selectedSchoolYearId, setSelectedSchoolYearId] = useState<number | null>(null);
  const [editingGroup, setEditingGroup] = useState<Group | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [rowError, setRowError] = useState<string | null>(null);

  const schools = schoolsQuery.data ?? [];
  const visibleSchoolYears = schoolYearsForSchool(
    schoolYearsQuery.data ?? [],
    selectedSchoolId,
  );
  const visibleGroups = groupsForSchoolYear(groupsQuery.data ?? [], selectedSchoolYearId);

  function handleCreate(input: { school_year: number; grado: number; grupo: string }) {
    setFormError(null);
    createMutation.mutate(input, {
      onError: (error) => setFormError(error.message),
    });
  }

  function handleUpdate(input: { school_year: number; grado: number; grupo: string }) {
    if (!editingGroup) return;
    setFormError(null);
    updateMutation.mutate(
      { id: editingGroup.id, input },
      {
        onSuccess: () => setEditingGroup(null),
        onError: (error) => setFormError(error.message),
      },
    );
  }

  function handleDelete(group: Group) {
    if (!window.confirm(`¿Eliminar el grupo "${group.grado}${group.grupo}"?`)) return;
    setRowError(null);
    deleteMutation.mutate(group.id, {
      // Surfaces the backend's PROTECT 4xx (a group with students cannot be
      // deleted) via the same ApiError/extractErrorMessage path.
      onError: (error) => setRowError(error.message),
    });
  }

  const columns = useMemo<ColumnDef<Group, unknown>[]>(
    () => [
      { header: "Grado", accessorKey: "grado" },
      { header: "Grupo", accessorKey: "grupo" },
      {
        id: "actions",
        header: "Acciones",
        cell: ({ row }) => (
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={() => setEditingGroup(row.original)}>
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
      <h1 className="text-xl font-semibold">Grupos</h1>

      <div className="flex flex-wrap gap-4">
        <label className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">Escuela</span>
          <select
            className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm"
            value={selectedSchoolId ?? ""}
            onChange={(event) => {
              setSelectedSchoolId(event.target.value ? Number(event.target.value) : null);
              setSelectedSchoolYearId(null);
              setEditingGroup(null);
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
              setEditingGroup(null);
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
      </div>

      {selectedSchoolYearId === null ? (
        <p className="text-muted-foreground">
          Selecciona una escuela y un ciclo escolar para ver sus grupos.
        </p>
      ) : (
        <>
          {editingGroup ? (
            <GroupForm
              schoolYearId={selectedSchoolYearId}
              initial={editingGroup}
              errorMessage={formError}
              isPending={updateMutation.isPending}
              onSubmit={handleUpdate}
              onCancel={() => {
                setEditingGroup(null);
                setFormError(null);
              }}
            />
          ) : (
            <GroupForm
              schoolYearId={selectedSchoolYearId}
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

          {groupsQuery.isLoading ? (
            <p className="text-muted-foreground">Cargando grupos…</p>
          ) : groupsQuery.isError ? (
            <p className="text-sm text-destructive" role="alert">
              No se pudieron cargar los grupos.
            </p>
          ) : (
            <DataTable columns={columns} data={visibleGroups} />
          )}
        </>
      )}
    </div>
  );
}
