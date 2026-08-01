"use client";

import { useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  CheckCircle2,
  Clock3,
  UserCheck,
  UserX,
} from "lucide-react";
import { DataTable } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { EstadoButton } from "@/components/ui/estado-button";
import { FormField } from "@/components/ui/form-field";
import { Select } from "@/components/ui/select";
import { StatCard } from "@/components/ui/stat-card";
import {
  countAttendanceStatuses,
  localTodayISO,
  rosterToDraft,
  useAttendanceBulkMutation,
  useAttendanceRosterQuery,
  type AttendanceRosterEntry,
  type AttendanceStatus,
  type DraftEntry,
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

type DraftRow = AttendanceRosterEntry & DraftEntry;

/** Daily attendance grid (attendance spec — Daily Attendance Screen, LXprh).
 * Draft state stays local until Guardar asistencia; Marcar todos presentes is
 * client-only. Periodo and Exportar are intentionally omitted. */
export default function AsistenciaPage() {
  const { groupId, setGroupId, visibleGroups } = useSchoolTeachingContext();
  const [date, setDate] = useState(localTodayISO);
  const [draft, setDraft] = useState<Map<number, DraftEntry>>(new Map());
  const [saveError, setSaveError] = useState<string | null>(null);

  const rosterQuery = useAttendanceRosterQuery(groupId, date);
  const bulkMutation = useAttendanceBulkMutation();

  useEffect(() => {
    if (!rosterQuery.isSuccess) return;
    setDraft(rosterToDraft(rosterQuery.data ?? []));
  }, [rosterQuery.data, rosterQuery.isSuccess, groupId, date]);

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

  const counts = countAttendanceStatuses(
    new Map(rows.map((row) => [row.student, { status: row.status, notes: row.notes }])),
  );

  function updateStudent(
    studentId: number,
    patch: Partial<DraftEntry>,
  ) {
    setDraft((prev) => {
      const next = new Map(prev);
      const current = next.get(studentId) ?? { status: "present" as AttendanceStatus, notes: "" };
      next.set(studentId, { ...current, ...patch });
      return next;
    });
  }

  function markAllPresent() {
    setDraft((prev) => {
      const next = new Map(prev);
      for (const studentId of next.keys()) {
        const current = next.get(studentId)!;
        next.set(studentId, { ...current, status: "present" });
      }
      return next;
    });
  }

  function handleSave() {
    if (groupId === null) return;
    setSaveError(null);
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
      { onError: (error) => setSaveError(error.message) },
    );
  }

  const columns = useMemo<ColumnDef<DraftRow, unknown>[]>(
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
            onChange={(event) =>
              updateStudent(row.original.student, { notes: event.target.value })
            }
          />
        ),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [rows],
  );

  const groupOptions = visibleGroups.map((group) => ({
    id: group.id,
    label: `${group.grado} ${group.grupo}`,
  }));

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Asistencia</h1>
          <p className="text-sm text-muted-foreground">Asistencia diaria</p>
        </div>
        <Button
          onClick={handleSave}
          disabled={groupId === null || bulkMutation.isPending || rows.length === 0}
        >
          Guardar asistencia
        </Button>
      </header>

      <div className="grid gap-4 rounded-xl bg-card p-5 shadow-card md:grid-cols-[1fr_1fr_auto]">
        <FormField label="Grupo">
          <Select
            value={groupId ?? ""}
            onChange={(event) =>
              setGroupId(event.target.value ? Number(event.target.value) : null)
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
            onChange={(event) => setDate(event.target.value)}
          />
        </FormField>
        <div className="flex items-end">
          <Button type="button" variant="outline" onClick={markAllPresent}>
            Marcar todos presentes
          </Button>
        </div>
      </div>

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

      {rosterQuery.isLoading ? (
        <p className="text-muted-foreground">Cargando roster…</p>
      ) : rosterQuery.isError ? (
        <p className="text-destructive">No se pudo cargar la asistencia.</p>
      ) : (
        <div className="rounded-xl bg-card p-0 shadow-card">
          <DataTable
            columns={columns}
            data={rows}
            emptyMessage={
              groupId === null
                ? "Selecciona un grupo para ver el roster."
                : "No hay alumnos en este grupo."
            }
          />
        </div>
      )}

      {rows.length > 0 && (
        <p className="text-sm text-muted-foreground">
          Mostrando 1–{rows.length} de {rows.length} alumnos
        </p>
      )}

      {saveError && <p className="text-sm text-destructive">{saveError}</p>}
    </div>
  );
}
