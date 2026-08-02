"use client";

import { useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock3,
  UserCheck,
  UserX,
} from "lucide-react";
import { DataTable } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { ChoiceChip } from "@/components/ui/choice-chip";
import { EstadoButton } from "@/components/ui/estado-button";
import { FormField } from "@/components/ui/form-field";
import { Select } from "@/components/ui/select";
import { StatCard } from "@/components/ui/stat-card";
import {
  countAttendanceStatuses,
  countWeekStatuses,
  formatWeekdayHeader,
  formatWeekRangeLabel,
  localTodayISO,
  mondayOf,
  rosterToDraft,
  shiftWeek,
  useAttendanceBulkMutation,
  useAttendanceRosterQuery,
  useAttendanceWeekBulkMutation,
  useAttendanceWeekQuery,
  weekDates,
  weekToDraft,
  type AttendanceRosterEntry,
  type AttendanceStatus,
  type DraftEntry,
  type WeekDraft,
} from "@/lib/api/attendance";
import { useSchoolTeachingContext } from "@/lib/school-context/school-teaching-context";

const STATUS_BUTTONS: {
  status: AttendanceStatus;
  label: string;
  tone: AttendanceStatus;
}[] = [
  { status: "present", label: "P", tone: "present" },
  { status: "absent", label: "A", tone: "absent" },
  { status: "late", label: "R", tone: "late" },
  { status: "excused", label: "J", tone: "excused" },
];

const STATUS_OPTIONS: { value: AttendanceStatus; label: string }[] = [
  { value: "present", label: "Presente" },
  { value: "absent", label: "Ausente" },
  { value: "late", label: "Retardo" },
  { value: "excused", label: "Justificado" },
];

type ViewMode = "daily" | "weekly";
type DraftRow = AttendanceRosterEntry & DraftEntry;

type WeekRow = {
  student: number;
  first_name: string;
  last_name_paternal: string;
  days: Record<string, AttendanceStatus>;
};

/** Daily + weekly attendance grids (attendance spec). Draft state stays local
 * until Guardar asistencia. Periodo and Exportar are intentionally omitted. */
export default function AsistenciaPage() {
  const { groupId, setGroupId, visibleGroups } = useSchoolTeachingContext();
  const [view, setView] = useState<ViewMode>("daily");
  const [date, setDate] = useState(localTodayISO);
  const [weekStart, setWeekStart] = useState(() => mondayOf(localTodayISO()));
  const [draft, setDraft] = useState<Map<number, DraftEntry>>(new Map());
  const [weekDraft, setWeekDraft] = useState<WeekDraft>(new Map());
  const [draftDirty, setDraftDirty] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const rosterQuery = useAttendanceRosterQuery(groupId, date);
  const weekQuery = useAttendanceWeekQuery(groupId, weekStart);
  const bulkMutation = useAttendanceBulkMutation();
  const weekBulkMutation = useAttendanceWeekBulkMutation();
  const saving =
    view === "daily" ? bulkMutation.isPending : weekBulkMutation.isPending;

  useEffect(() => {
    setDraftDirty(false);
  }, [groupId, date, weekStart, view]);

  useEffect(() => {
    if (!rosterQuery.isSuccess || draftDirty || view !== "daily") return;
    setDraft(rosterToDraft(rosterQuery.data ?? []));
  }, [rosterQuery.data, rosterQuery.isSuccess, draftDirty, view]);

  useEffect(() => {
    if (!weekQuery.isSuccess || draftDirty || view !== "weekly") return;
    if (weekQuery.data) setWeekDraft(weekToDraft(weekQuery.data));
  }, [weekQuery.data, weekQuery.isSuccess, draftDirty, view]);

  const rows = useMemo<DraftRow[]>(() => {
    const roster = rosterQuery.data ?? [];
    return roster.map((row) => {
      const entry = draft.get(row.student) ?? {
        status: "present" as AttendanceStatus,
        notes: row.notes,
      };
      return { ...row, ...entry };
    });
  }, [rosterQuery.data, draft]);

  const weekRows = useMemo<WeekRow[]>(() => {
    const students = weekQuery.data?.students ?? [];
    const dates = weekQuery.data?.dates ?? weekDates(weekStart);
    return students.map((row) => {
      const days = weekDraft.get(row.student) ?? { ...row.days };
      const filled: Record<string, AttendanceStatus> = {};
      for (const d of dates) {
        filled[d] = days[d] ?? "present";
      }
      return {
        student: row.student,
        first_name: row.first_name,
        last_name_paternal: row.last_name_paternal,
        days: filled,
      };
    });
  }, [weekQuery.data, weekDraft, weekStart]);

  const dailyCounts = countAttendanceStatuses(
    new Map(
      rows.map((row) => [row.student, { status: row.status, notes: row.notes }]),
    ),
  );
  const weekCounts = countWeekStatuses(
    new Map(weekRows.map((row) => [row.student, row.days])),
  );
  const counts = view === "daily" ? dailyCounts : weekCounts;

  function updateStudent(studentId: number, patch: Partial<DraftEntry>) {
    if (saving) return;
    setDraftDirty(true);
    setDraft((prev) => {
      const next = new Map(prev);
      const current = next.get(studentId) ?? {
        status: "present" as AttendanceStatus,
        notes: "",
      };
      next.set(studentId, { ...current, ...patch });
      return next;
    });
  }

  function updateWeekCell(
    studentId: number,
    cellDate: string,
    status: AttendanceStatus,
  ) {
    if (saving) return;
    setDraftDirty(true);
    setWeekDraft((prev) => {
      const next = new Map(prev);
      const current = { ...(next.get(studentId) ?? {}) };
      current[cellDate] = status;
      next.set(studentId, current);
      return next;
    });
  }

  function markAllPresent() {
    if (saving) return;
    setDraftDirty(true);
    if (view === "daily") {
      setDraft((prev) => {
        const next = new Map(prev);
        for (const studentId of next.keys()) {
          const current = next.get(studentId)!;
          next.set(studentId, { ...current, status: "present" });
        }
        return next;
      });
      return;
    }
    const dates = weekQuery.data?.dates ?? weekDates(weekStart);
    setWeekDraft((prev) => {
      const next = new Map(prev);
      for (const studentId of next.keys()) {
        const days: Record<string, AttendanceStatus> = {};
        for (const d of dates) days[d] = "present";
        next.set(studentId, days);
      }
      return next;
    });
  }

  function handleSave() {
    if (groupId === null || saving) return;
    setSaveError(null);

    if (view === "daily") {
      if (rows.length === 0) return;
      bulkMutation.mutate(
        {
          group: groupId,
          date,
          entries: rows.map((row) => ({
            student: row.student,
            status: row.status,
            notes: row.notes,
          })),
        },
        {
          onSuccess: () => setDraftDirty(false),
          onError: (error) => setSaveError(error.message),
        },
      );
      return;
    }

    if (weekRows.length === 0) return;
    const dates = weekQuery.data?.dates ?? weekDates(weekStart);
    const entries = weekRows.flatMap((row) =>
      dates.map((d) => ({
        student: row.student,
        date: d,
        status: row.days[d] ?? ("present" as AttendanceStatus),
      })),
    );
    weekBulkMutation.mutate(
      { group: groupId, week_start: weekStart, entries },
      {
        onSuccess: () => setDraftDirty(false),
        onError: (error) => setSaveError(error.message),
      },
    );
  }

  const dailyColumns = useMemo<ColumnDef<DraftRow, unknown>[]>(
    () => [
      {
        header: "#",
        cell: ({ row }) => row.index + 1,
      },
      {
        header: "Alumno",
        cell: ({ row }) =>
          `${row.original.first_name} ${row.original.last_name_paternal}`,
      },
      {
        header: "CURP",
        accessorFn: (row) => row.curp || "—",
      },
      {
        header: "Estado",
        cell: ({ row }) => (
          <div className="flex gap-1">
            {STATUS_BUTTONS.map(({ status, label, tone }) => (
              <EstadoButton
                key={status}
                aria-label={
                  status === "present"
                    ? "Presente"
                    : status === "absent"
                      ? "Ausente"
                      : status === "late"
                        ? "Retardo"
                        : "Justificado"
                }
                attendanceTone={tone}
                selected={row.original.status === status}
                disabled={saving}
                onClick={() => updateStudent(row.original.student, { status })}
              >
                {label}
              </EstadoButton>
            ))}
          </div>
        ),
      },
      {
        header: "Observación",
        cell: ({ row }) => (
          <input
            aria-label="Observación"
            className="w-full rounded-md border border-input bg-background px-2 py-1 text-sm"
            value={row.original.notes}
            disabled={saving}
            onChange={(event) =>
              updateStudent(row.original.student, {
                notes: event.target.value,
              })
            }
          />
        ),
      },
    ],
    [rows, saving],
  );

  const dates = weekQuery.data?.dates ?? weekDates(weekStart);

  const weekColumns = useMemo<ColumnDef<WeekRow, unknown>[]>(() => {
    const cols: ColumnDef<WeekRow, unknown>[] = [
      {
        header: "#",
        cell: ({ row }) => row.index + 1,
      },
      {
        header: "Alumno",
        cell: ({ row }) =>
          `${row.original.first_name} ${row.original.last_name_paternal}`,
      },
    ];
    dates.forEach((iso, index) => {
      cols.push({
        id: iso,
        header: formatWeekdayHeader(iso, index),
        cell: ({ row }) => (
          <Select
            aria-label={`${row.original.first_name} ${formatWeekdayHeader(iso, index)}`}
            className="h-9 min-w-[7.5rem] text-xs"
            value={row.original.days[iso] ?? "present"}
            disabled={saving}
            onChange={(event) =>
              updateWeekCell(
                row.original.student,
                iso,
                event.target.value as AttendanceStatus,
              )
            }
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
        ),
      });
    });
    return cols;
  }, [dates, saving, weekRows]);

  const groupOptions = visibleGroups.map((group) => ({
    id: group.id,
    label: `${group.grado} ${group.grupo}`,
  }));

  const tableRows = view === "daily" ? rows : weekRows;
  const isLoading =
    view === "daily" ? rosterQuery.isLoading : weekQuery.isLoading;
  const isError = view === "daily" ? rosterQuery.isError : weekQuery.isError;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-3">
          <div>
            <h1 className="text-2xl font-semibold">Asistencia</h1>
            <p className="text-sm text-muted-foreground">
              {view === "daily" ? "Asistencia diaria" : "Asistencia semanal"}
            </p>
          </div>
          <div
            className="flex flex-wrap gap-2"
            role="group"
            aria-label="Vista de asistencia"
          >
            <ChoiceChip
              selected={view === "daily"}
              onClick={() => setView("daily")}
            >
              Diaria
            </ChoiceChip>
            <ChoiceChip
              selected={view === "weekly"}
              onClick={() => setView("weekly")}
            >
              Semanal
            </ChoiceChip>
          </div>
        </div>
        <Button
          onClick={handleSave}
          disabled={groupId === null || saving || tableRows.length === 0}
        >
          Guardar asistencia
        </Button>
      </header>

      {view === "daily" ? (
        <div className="grid gap-4 rounded-xl bg-card p-5 shadow-card md:grid-cols-[1fr_1fr_auto]">
          <FormField label="Grupo">
            <Select
              value={groupId ?? ""}
              disabled={saving}
              onChange={(event) =>
                setGroupId(
                  event.target.value ? Number(event.target.value) : null,
                )
              }
            >
              <option value="">Selecciona un grupo…</option>
              {groupOptions.map((group) => (
                <option key={group.id} value={group.id}>
                  {group.label}
                </option>
              ))}
            </Select>
          </FormField>
          <FormField label="Fecha">
            <input
              type="date"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={date}
              disabled={saving}
              onChange={(event) => setDate(event.target.value)}
            />
          </FormField>
          <div className="flex items-end">
            <Button
              type="button"
              variant="outline"
              disabled={saving}
              onClick={markAllPresent}
            >
              Marcar todos presentes
            </Button>
          </div>
        </div>
      ) : (
        <div className="grid gap-4 rounded-xl bg-card p-5 shadow-card md:grid-cols-[1fr_auto_auto]">
          <FormField label="Grupo">
            <Select
              value={groupId ?? ""}
              disabled={saving}
              onChange={(event) =>
                setGroupId(
                  event.target.value ? Number(event.target.value) : null,
                )
              }
            >
              <option value="">Selecciona un grupo…</option>
              {groupOptions.map((group) => (
                <option key={group.id} value={group.id}>
                  {group.label}
                </option>
              ))}
            </Select>
          </FormField>
          <FormField label="Semana">
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="icon"
                aria-label="Semana anterior"
                disabled={saving}
                onClick={() => setWeekStart((prev) => shiftWeek(prev, -1))}
              >
                <ChevronLeft className="size-4" />
              </Button>
              <span className="min-w-[9rem] text-center text-sm font-medium">
                {formatWeekRangeLabel(weekStart)}
              </span>
              <Button
                type="button"
                variant="outline"
                size="icon"
                aria-label="Semana siguiente"
                disabled={saving}
                onClick={() => setWeekStart((prev) => shiftWeek(prev, 1))}
              >
                <ChevronRight className="size-4" />
              </Button>
            </div>
          </FormField>
          <div className="flex items-end">
            <Button
              type="button"
              variant="outline"
              disabled={saving}
              onClick={markAllPresent}
            >
              Marcar todos presentes
            </Button>
          </div>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Presentes"
          value={counts.present}
          attendanceTone="present"
          icon={<UserCheck aria-hidden className="size-5" />}
        />
        <StatCard
          label="Ausentes"
          value={counts.absent}
          attendanceTone="absent"
          icon={<UserX aria-hidden className="size-5" />}
        />
        <StatCard
          label="Retardos"
          value={counts.late}
          attendanceTone="late"
          icon={<Clock3 aria-hidden className="size-5" />}
        />
        <StatCard
          label="Justificados"
          value={counts.excused}
          attendanceTone="excused"
          icon={<CheckCircle2 aria-hidden className="size-5" />}
        />
      </div>

      {isLoading ? (
        <p className="text-muted-foreground">Cargando roster…</p>
      ) : isError ? (
        <p className="text-destructive">No se pudo cargar la asistencia.</p>
      ) : (
        <div className="overflow-x-auto rounded-xl bg-card p-0 shadow-card">
          {view === "daily" ? (
            <DataTable
              columns={dailyColumns}
              data={rows}
              emptyMessage={
                groupId === null
                  ? "Selecciona un grupo para ver el roster."
                  : "No hay alumnos en este grupo."
              }
            />
          ) : (
            <DataTable
              columns={weekColumns}
              data={weekRows}
              emptyMessage={
                groupId === null
                  ? "Selecciona un grupo para ver el roster."
                  : "No hay alumnos en este grupo."
              }
            />
          )}
        </div>
      )}

      {tableRows.length > 0 && (
        <p className="text-sm text-muted-foreground">
          Mostrando 1–{tableRows.length} de {tableRows.length} alumnos
        </p>
      )}

      {saveError && <p className="text-sm text-destructive">{saveError}</p>}
    </div>
  );
}
