"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";
import {
  BookOpen,
  CheckCircle2,
  Clock3,
  FilePlus2,
  Plus,
  Sparkles,
} from "lucide-react";
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
import { GenerateForm, AVAILABLE_CAMPOS } from "./generate-form";
import { StatusChip } from "@/components/ui/status-chip";
import { Card } from "@/components/ui/card";

type StatusFilter = "all" | LessonPlan["status"];

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
  const [campoFilter, setCampoFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [showGenerateForm, setShowGenerateForm] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [rowError, setRowError] = useState<string | null>(null);

  const schools = schoolsQuery.data ?? [];
  const visibleSchoolYears = schoolYearsForSchool(
    schoolYearsQuery.data ?? [],
    selectedSchoolId,
  );
  const visibleGroups = groupsForSchoolYear(groupsQuery.data ?? [], selectedSchoolYearId);
  const groupPlans = lessonPlansForGroup(lessonPlansQuery.data ?? [], selectedGroupId);
  const visiblePlans = groupPlans.filter(
    (plan) =>
      (campoFilter === "all" || plan.campo === campoFilter) &&
      (statusFilter === "all" || plan.status === statusFilter),
  );

  const stats = [
      {
        label: "Proyectos activos",
        value: groupPlans.filter((plan) => plan.status !== "failed").length,
        caption: "en este grupo",
        icon: BookOpen,
        tone: "text-primary bg-primary/10",
      },
      {
        label: "Planeaciones listas",
        value: groupPlans.filter((plan) => plan.status === "ready").length,
        caption: `de ${groupPlans.length} planeaciones`,
        icon: CheckCircle2,
        tone: "text-success bg-success/10",
      },
      {
        label: "Generando",
        value: groupPlans.filter((plan) => plan.status === "pending").length,
        caption: "en proceso con IA",
        icon: Sparkles,
        tone: "text-primary bg-primary/10",
      },
      {
        label: "Requieren atención",
        value: groupPlans.filter((plan) => plan.status === "failed").length,
        caption: "con error de generación",
        icon: Clock3,
        tone: "text-destructive bg-destructive/10",
      },
    ];

  function handleGenerate(input: { group: number; campo: string; grade: string; theme: string }) {
    setFormError(null);
    createMutation.mutate(input, {
      onSuccess: () => setShowGenerateForm(false),
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
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Planeaciones</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Proyectos por campo formativo, generados con IA y aprobados por ti
          </p>
        </div>
        <Button
          size="lg"
          className="shadow-[0_2px_6px_color-mix(in_oklch,var(--primary),transparent_68%)]"
          disabled={selectedGroupId === null}
          onClick={() => setShowGenerateForm((visible) => !visible)}
        >
          <Plus />
          Nueva planeación
        </Button>
      </header>

      <Card className="grid gap-4 p-5 sm:grid-cols-2 xl:grid-cols-5">
        <SelectField
          label="Escuela"
          value={selectedSchoolId ?? ""}
          onChange={(value) => {
            setSelectedSchoolId(value ? Number(value) : null);
            setSelectedSchoolYearId(null);
            setSelectedGroupId(null);
            setFormError(null);
          }}
        >
          <option value="">Selecciona una escuela…</option>
          {schools.map((school) => (
            <option key={school.id} value={school.id}>{school.name}</option>
          ))}
        </SelectField>

        <SelectField
          label="Ciclo escolar"
          value={selectedSchoolYearId ?? ""}
          disabled={selectedSchoolId === null}
          onChange={(value) => {
            setSelectedSchoolYearId(value ? Number(value) : null);
            setSelectedGroupId(null);
            setFormError(null);
          }}
        >
          <option value="">Selecciona un ciclo…</option>
          {visibleSchoolYears.map((schoolYear) => (
            <option key={schoolYear.id} value={schoolYear.id}>{schoolYear.label}</option>
          ))}
        </SelectField>

        <SelectField
          label="Grupo"
          value={selectedGroupId ?? ""}
          disabled={selectedSchoolYearId === null}
          onChange={(value) => {
            setSelectedGroupId(value ? Number(value) : null);
            setFormError(null);
          }}
        >
          <option value="">Selecciona un grupo…</option>
          {visibleGroups.map((group) => (
            <option key={group.id} value={group.id}>{group.grado}° {group.grupo}</option>
          ))}
        </SelectField>

        <SelectField label="Campo formativo" value={campoFilter} onChange={setCampoFilter}>
          <option value="all">Todos</option>
          {AVAILABLE_CAMPOS.map((campo) => <option key={campo} value={campo}>{campo}</option>)}
        </SelectField>

        <SelectField
          label="Estado"
          value={statusFilter}
          onChange={(value) => setStatusFilter(value as StatusFilter)}
        >
          <option value="all">Todos</option>
          <option value="ready">Lista</option>
          <option value="pending">Generando</option>
          <option value="failed">Con error</option>
        </SelectField>
      </Card>

      {showGenerateForm && selectedGroupId !== null ? (
        <GenerateForm
          groupId={selectedGroupId}
          defaultGrade={String(visibleGroups.find((group) => group.id === selectedGroupId)?.grado ?? "")}
          errorMessage={formError}
          isPending={createMutation.isPending}
          onSubmit={handleGenerate}
        />
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map(({ label, value, caption, icon: Icon, tone }) => (
          <Card key={label} className="flex flex-col gap-2 p-5">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-muted-foreground">{label}</span>
              <span className={`flex size-9 items-center justify-center rounded-lg ${tone}`}>
                <Icon className="size-4" />
              </span>
            </div>
            <strong className="text-2xl font-medium">{value}</strong>
            <span className="text-xs text-muted-foreground">{caption}</span>
          </Card>
        ))}
      </div>

      {rowError ? <p className="text-sm text-destructive" role="alert">{rowError}</p> : null}

      {selectedGroupId === null ? (
        <Card className="flex min-h-56 flex-col items-center justify-center gap-3 border border-dashed bg-card/50 text-center shadow-none">
          <span className="flex size-12 items-center justify-center rounded-full bg-primary/10 text-primary">
            <BookOpen className="size-5" />
          </span>
          <div>
            <p className="font-medium">Selecciona un grupo</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Elige escuela, ciclo escolar y grupo para ver sus planeaciones.
            </p>
          </div>
        </Card>
      ) : lessonPlansQuery.isLoading ? (
        <p className="text-muted-foreground">Cargando planeaciones…</p>
      ) : lessonPlansQuery.isError ? (
        <p className="text-sm text-destructive" role="alert">No se pudieron cargar las planeaciones.</p>
      ) : visiblePlans.length === 0 ? (
        <Card className="flex min-h-56 flex-col items-center justify-center gap-3 border border-dashed bg-card/50 text-center shadow-none">
          <FilePlus2 className="size-8 text-primary" />
          <div>
            <p className="font-medium">Aún no hay planeaciones</p>
            <p className="mt-1 text-sm text-muted-foreground">Crea la primera planeación para este grupo.</p>
          </div>
        </Card>
      ) : (
        <Card className="p-0"><DataTable columns={columns} data={visiblePlans} /></Card>
      )}
    </div>
  );
}

function SelectField({
  label,
  value,
  disabled,
  onChange,
  children,
}: {
  label: string;
  value: string | number;
  disabled?: boolean;
  onChange: (value: string) => void;
  children: React.ReactNode;
}) {
  return (
    <label className="flex min-w-0 flex-col gap-1.5 text-sm">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      <select
        className="h-10 min-w-0 rounded-md border border-input bg-background px-3 text-sm outline-none transition-shadow focus:ring-2 focus:ring-ring/40 disabled:cursor-not-allowed disabled:opacity-50"
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      >
        {children}
      </select>
    </label>
  );
}

function StatusBadge({ status }: { status: LessonPlan["status"] }) {
  if (status === "ready") return <StatusChip tone="success">Aprobada</StatusChip>;
  if (status === "failed") return <StatusChip tone="danger">Con error</StatusChip>;
  return <StatusChip tone="brand">Borrador IA</StatusChip>;
}
