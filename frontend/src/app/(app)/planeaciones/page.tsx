"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/data-table";
import { useSchoolsQuery } from "@/lib/api/schools";
import { schoolYearsForSchool, useSchoolYearsQuery } from "@/lib/api/school-years";
import { groupsForSchoolYear, useGroupsQuery } from "@/lib/api/groups";
import {
  lessonPlansForGroup,
  useCreateLessonPlanMutation,
  useDeleteLessonPlanMutation,
  useLessonPlansQuery,
  type LessonPlan,
} from "@/lib/api/lesson-plans";
import { GenerateForm } from "./generate-form";
import { StatusChip } from "@/components/ui/status-chip";
import { Card } from "@/components/ui/card";

/** Planeaciones list + generate screen, scoped to one selected School →
 * SchoolYear → Group (ai-planeaciones spec — "CRUD Endpoints Are Workspace-
 * Scoped", "Generation Request Is Gated, Workspace-Bound, and Schema-
 * Validated"; the exit-gate walkthrough: teacher selects group → generates →
 * polls to ready → views → exports docx). `/api/lesson-plans/` has no
 * server-side `?group=` filter typed in the client, so the picked group
 * narrows the list client-side (mirrors `groups`/`students` screens). */
export default function PlaneacionesPage() {
  const schoolsQuery = useSchoolsQuery();
  const schoolYearsQuery = useSchoolYearsQuery();
  const groupsQuery = useGroupsQuery();
  const lessonPlansQuery = useLessonPlansQuery();
  const createMutation = useCreateLessonPlanMutation();
  const deleteMutation = useDeleteLessonPlanMutation();

  const [selectedSchoolId, setSelectedSchoolId] = useState<number | null>(null);
  const [selectedSchoolYearId, setSelectedSchoolYearId] = useState<number | null>(null);
  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [rowError, setRowError] = useState<string | null>(null);

  const schools = schoolsQuery.data ?? [];
  const visibleSchoolYears = schoolYearsForSchool(
    schoolYearsQuery.data ?? [],
    selectedSchoolId,
  );
  const visibleGroups = groupsForSchoolYear(groupsQuery.data ?? [], selectedSchoolYearId);
  const visiblePlans = lessonPlansForGroup(lessonPlansQuery.data ?? [], selectedGroupId);

  function handleGenerate(input: { group: number; campo: string; grade: string; theme: string }) {
    setFormError(null);
    createMutation.mutate(input, {
      onError: (error) => setFormError(error.message),
    });
  }

  function handleDelete(plan: LessonPlan) {
    if (!window.confirm(`¿Eliminar la planeación "${plan.theme}"?`)) return;
    setRowError(null);
    deleteMutation.mutate(plan.id, {
      onError: (error) => setRowError(error.message),
    });
  }

  const columns = useMemo<ColumnDef<LessonPlan, unknown>[]>(
    () => [
      { header: "Tema", accessorKey: "theme" },
      { header: "Campo formativo", accessorKey: "campo" },
      {
        header: "Estado",
        cell: ({ row }) => <StatusBadge status={row.original.status} />,
      },
      {
        id: "actions",
        header: "Acciones",
        cell: ({ row }) => (
          <div className="flex gap-2">
            <Link
              href={`/planeaciones/${row.original.id}`}
              className="text-sm font-medium text-primary underline-offset-4 hover:underline"
            >
              Ver
            </Link>
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
      <h1 className="text-xl font-semibold">Planeaciones</h1>

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
          Selecciona una escuela, un ciclo escolar y un grupo para ver sus planeaciones.
        </p>
      ) : (
        <>
          <GenerateForm
            groupId={selectedGroupId}
            defaultGrade={String(visibleGroups.find((g) => g.id === selectedGroupId)?.grado ?? "")}
            errorMessage={formError}
            isPending={createMutation.isPending}
            onSubmit={handleGenerate}
          />

          {rowError ? (
            <p className="text-sm text-destructive" role="alert">
              {rowError}
            </p>
          ) : null}

          {lessonPlansQuery.isLoading ? (
            <p className="text-muted-foreground">Cargando planeaciones…</p>
          ) : lessonPlansQuery.isError ? (
            <p className="text-sm text-destructive" role="alert">
              No se pudieron cargar las planeaciones.
            </p>
          ) : (
            <Card className="p-0"><DataTable columns={columns} data={visiblePlans} /></Card>
          )}
        </>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: LessonPlan["status"] }) {
  if (status === "ready") {
    return <StatusChip tone="success">Lista</StatusChip>;
  }
  if (status === "failed") {
    return <StatusChip tone="danger">Falló</StatusChip>;
  }
  return <StatusChip tone="brand">Generando…</StatusChip>;
}
