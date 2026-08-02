"use client";

import { useMemo, useState } from "react";
import {
  Calculator,
  CircleCheck,
  ListChecks,
  TriangleAlert,
  TrendingUp,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ChoiceChip } from "@/components/ui/choice-chip";
import { FormField } from "@/components/ui/form-field";
import { Select } from "@/components/ui/select";
import { StatCard } from "@/components/ui/stat-card";
import {
  useActivitiesQuery,
  useBulkUpsertScoresMutation,
  useCreateActivityMutation,
  useScoreMatrixQuery,
  type ActivitiesFilters,
  type ActivityCreate,
  type ScoresBulkRequest,
  type Term,
  type TypeEnum,
} from "@/lib/api/grades";

type ScoreBulkEntry = ScoresBulkRequest["entries"][number];
import {
  useLessonPlanCatalogQuery,
  useLessonPlanFieldsQuery,
} from "@/lib/api/lesson-plan-catalog";
import { useSchoolTeachingContext } from "@/lib/school-context/school-teaching-context";

type ViewMode = "by-activity" | "by-student";
type ModalDraft = {
  title: string;
  type: TypeEnum | "";
  due_date: string;
  field: string;
  subject_ids: string[];
  description: string;
};

const TYPE_LABELS: Record<TypeEnum, string> = {
  task: "Tarea",
  activity: "Actividad",
  project: "Proyecto",
  exam: "Examen",
};
const FALLBACK_TERMS: Term[] = [
  { id: 1, number: 1 },
  { id: 2, number: 2 },
  { id: 3, number: 3 },
];
const EMPTY: ModalDraft = {
  title: "",
  type: "",
  due_date: "",
  field: "",
  subject_ids: [],
  description: "",
};
const fieldCls =
  "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm";
const cellCls =
  "h-9 w-16 rounded-md border border-input bg-background px-2 text-center text-sm";

/** Draft Map key: `${studentId}:${activityId}` */
export function scoreDraftKey(studentId: number, activityId: number) {
  return `${studentId}:${activityId}`;
}

/** null/undefined = unscored (empty display); never coerce to 0.0 */
export function displayScore(score: string | null | undefined): string {
  return score == null ? "" : score;
}

/** null average → em dash for stats card */
export function displayAverage(score: string | null | undefined): string {
  return score == null || score === "" ? "—" : score;
}

function parseDraftEntries(draft: Map<string, string>): ScoreBulkEntry[] {
  const entries: ScoreBulkEntry[] = [];
  for (const [key, raw] of draft) {
    const [studentRaw, activityRaw] = key.split(":");
    const student = Number(studentRaw);
    const activity = Number(activityRaw);
    if (!Number.isFinite(student) || !Number.isFinite(activity)) continue;
    const trimmed = raw.trim();
    entries.push({
      student,
      activity,
      score: trimmed === "" ? null : trimmed,
    });
  }
  return entries;
}

function buildListFilters(
  field: string,
  subject: string,
  type: TypeEnum | "",
  q: string,
): ActivitiesFilters {
  return {
    ...(field ? { field } : {}),
    ...(subject ? { subject } : {}),
    ...(type ? { type } : {}),
    ...(q.trim() ? { q: q.trim() } : {}),
  };
}

export default function ActividadesPage() {
  const { groupId, setGroupId, visibleGroups } = useSchoolTeachingContext();
  const [view, setView] = useState<ViewMode>("by-activity");
  const [termId, setTermId] = useState<number | null>(null);
  const [fieldFilter, setFieldFilter] = useState("");
  const [subjectFilter, setSubjectFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState<TypeEnum | "">("");
  const [qFilter, setQFilter] = useState("");
  const [open, setOpen] = useState(false);
  const [modal, setModal] = useState<ModalDraft>(EMPTY);
  const [formError, setFormError] = useState<string | null>(null);
  const [draft, setDraft] = useState<Map<string, string>>(() => new Map());

  const listFilters = useMemo(
    () => buildListFilters(fieldFilter, subjectFilter, typeFilter, qFilter),
    [fieldFilter, subjectFilter, typeFilter, qFilter],
  );
  const matrixFilters = useMemo(
    () => ({
      ...(fieldFilter ? { field: fieldFilter } : {}),
      ...(subjectFilter ? { subject: subjectFilter } : {}),
      ...(typeFilter ? { type: typeFilter } : {}),
    }),
    [fieldFilter, subjectFilter, typeFilter],
  );

  const listQ = useActivitiesQuery(groupId, termId, listFilters);
  const matrixQ = useScoreMatrixQuery(
    groupId,
    view === "by-student" ? termId : null,
    matrixFilters,
  );
  const createM = useCreateActivityMutation();
  const bulkM = useBulkUpsertScoresMutation();
  const fieldsQ = useLessonPlanFieldsQuery();
  const catalogQ = useLessonPlanCatalogQuery(groupId, open ? modal.field : fieldFilter);

  const terms = listQ.data?.terms ?? matrixQ.data?.terms ?? FALLBACK_TERMS;
  const activities = termId === null ? [] : (listQ.data?.activities ?? []);
  const stats = termId === null ? null : (listQ.data?.stats ?? null);
  const matrixStudents = matrixQ.data?.students ?? [];
  const matrixActivities = matrixQ.data?.activities ?? [];
  const subjects = catalogQ.data?.subjects ?? [];
  const groups = useMemo(
    () => visibleGroups.map((g) => ({ id: g.id, label: `${g.grado} ${g.grupo}` })),
    [visibleGroups],
  );
  const selectedTerm = terms.find((t) => t.id === termId);

  const serverScores = useMemo(() => {
    const map = new Map<string, string | null>();
    for (const cell of matrixQ.data?.scores ?? []) {
      map.set(scoreDraftKey(cell.student, cell.activity), cell.score);
    }
    return map;
  }, [matrixQ.data?.scores]);

  function cellValue(studentId: number, activityId: number): string {
    const key = scoreDraftKey(studentId, activityId);
    if (draft.has(key)) return draft.get(key)!;
    return displayScore(serverScores.get(key));
  }

  function setCellDraft(studentId: number, activityId: number, value: string) {
    const key = scoreDraftKey(studentId, activityId);
    setDraft((prev) => {
      const next = new Map(prev);
      next.set(key, value);
      return next;
    });
  }

  function close() {
    setOpen(false);
    setFormError(null);
    setModal(EMPTY);
  }

  function submit() {
    if (groupId === null || termId === null) return;
    if (!modal.title.trim() || !modal.type || !modal.due_date || !modal.field || !modal.subject_ids.length) {
      setFormError("Completa título, tipo, entrega, campo y al menos una asignatura.");
      return;
    }
    const payload: ActivityCreate = {
      group: groupId,
      term: termId,
      title: modal.title.trim(),
      type: modal.type,
      due_date: modal.due_date,
      field: modal.field,
      subject_ids: modal.subject_ids,
      description: modal.description,
    };
    setFormError(null);
    createM.mutate(payload, {
      onSuccess: () => close(),
      onError: (e) => setFormError(e.message),
    });
  }

  function saveScores() {
    if (groupId === null || draft.size === 0) return;
    bulkM.mutate(
      { group: groupId, entries: parseDraftEntries(draft) },
      {
        onSuccess: () => setDraft(new Map()),
      },
    );
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-3">
          <h1 className="text-2xl font-semibold">Actividades</h1>
          <div className="flex flex-wrap gap-2" role="group" aria-label="Vista de actividades">
            <ChoiceChip selected={view === "by-activity"} onClick={() => setView("by-activity")}>
              Por actividad
            </ChoiceChip>
            <ChoiceChip selected={view === "by-student"} onClick={() => setView("by-student")}>
              Por alumno
            </ChoiceChip>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {view === "by-student" ? (
            <Button
              type="button"
              disabled={groupId === null || termId === null || draft.size === 0 || bulkM.isPending}
              onClick={saveScores}
            >
              Guardar
            </Button>
          ) : null}
          <Button
            type="button"
            disabled={groupId === null || termId === null}
            onClick={() => {
              setFormError(null);
              setModal(EMPTY);
              setOpen(true);
            }}
          >
            Nueva actividad
          </Button>
        </div>
      </header>

      <div
        data-banner="calificaciones"
        className="flex flex-wrap items-center gap-2.5 rounded-lg border border-primary/20 bg-primary/5 px-4 py-3 text-sm"
        role="note"
      >
        <Calculator className="size-4 shrink-0 text-primary" aria-hidden />
        <span className="font-semibold">Estas calificaciones alimentan Calificaciones</span>
        <span className="text-muted-foreground">
          · el promedio de cada asignatura en el periodo se calcula con el promedio simple de sus
          actividades.
        </span>
      </div>

      <div className="grid gap-4 rounded-xl bg-card p-5 shadow-card sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
        <FormField label="Grupo">
          <Select
            aria-label="Grupo"
            value={groupId ?? ""}
            onChange={(e) => setGroupId(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">Selecciona un grupo…</option>
            {groups.map((g) => (
              <option key={g.id} value={g.id}>{g.label}</option>
            ))}
          </Select>
        </FormField>
        <FormField label="Campo formativo">
          <Select
            name="fieldFilter"
            aria-label="Campo formativo"
            value={fieldFilter}
            onChange={(e) => {
              setFieldFilter(e.target.value);
              setSubjectFilter("");
            }}
          >
            <option value="">Todos los campos</option>
            {(fieldsQ.data ?? []).map((f) => (
              <option key={f.id} value={f.id}>{f.name}</option>
            ))}
          </Select>
        </FormField>
        <FormField label="Asignatura">
          <Select
            name="subjectFilter"
            aria-label="Asignatura"
            value={subjectFilter}
            disabled={fieldFilter === ""}
            onChange={(e) => setSubjectFilter(e.target.value)}
          >
            <option value="">Todas</option>
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </Select>
        </FormField>
        <FormField label="Tipo">
          <Select
            name="typeFilter"
            aria-label="Tipo"
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value as TypeEnum | "")}
          >
            <option value="">Todos los tipos</option>
            {(Object.keys(TYPE_LABELS) as TypeEnum[]).map((v) => (
              <option key={v} value={v}>{TYPE_LABELS[v]}</option>
            ))}
          </Select>
        </FormField>
        <FormField label="Periodo" required>
          <Select
            name="termId"
            aria-label="Periodo"
            value={termId ?? ""}
            onChange={(e) => {
              setTermId(e.target.value ? Number(e.target.value) : null);
              setDraft(new Map());
            }}
          >
            <option value="">Selecciona un periodo…</option>
            {terms.map((t) => (
              <option key={t.id} value={t.id}>Periodo {t.number}</option>
            ))}
          </Select>
        </FormField>
        {view === "by-activity" ? (
          <FormField label="Buscar">
            <input
              name="qFilter"
              aria-label="Buscar"
              className={fieldCls}
              placeholder="Título de actividad"
              value={qFilter}
              onChange={(e) => setQFilter(e.target.value)}
            />
          </FormField>
        ) : null}
      </div>

      {stats ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Actividades del periodo"
            value={<span data-stat="total">{stats.total_activities}</span>}
            caption={selectedTerm ? `Periodo ${selectedTerm.number}` : "Periodo"}
            tone="brand"
            icon={<ListChecks className="size-4" aria-hidden />}
          />
          <StatCard
            label="Calificadas"
            value={<span data-stat="graded">{stats.graded_activities}</span>}
            caption={`de ${stats.total_activities} actividades`}
            tone="success"
            icon={<CircleCheck className="size-4" aria-hidden />}
          />
          <StatCard
            label="Pendientes por calificar"
            value={<span data-stat="pending">{stats.pending_activities}</span>}
            caption="entregas sin registrar"
            tone="neutral"
            icon={<TriangleAlert className="size-4" aria-hidden />}
          />
          <StatCard
            label="Promedio de actividades"
            value={<span data-stat="average">{displayAverage(stats.average_score)}</span>}
            caption="alimenta Calificaciones"
            tone="brand"
            icon={<TrendingUp className="size-4" aria-hidden />}
          />
        </div>
      ) : null}

      {view === "by-student" ? (
        termId === null ? (
          <p className="text-muted-foreground">Selecciona un periodo para ver la matriz.</p>
        ) : matrixQ.isLoading ? (
          <p className="text-muted-foreground">Cargando matriz…</p>
        ) : matrixQ.isError ? (
          <p className="text-destructive">No se pudo cargar la matriz de calificaciones.</p>
        ) : matrixStudents.length === 0 || matrixActivities.length === 0 ? (
          <p className="text-muted-foreground">No hay alumnos o actividades en este periodo.</p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-border">
            <table className="w-full text-sm">
              <thead className="bg-muted/40 text-left text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="sticky left-0 bg-muted/40 px-4 py-3 font-medium">Alumno</th>
                  {matrixActivities.map((a) => (
                    <th key={a.id} className="px-3 py-3 font-medium">
                      <div className="max-w-[8rem] truncate normal-case">{a.title}</div>
                      <div className="mt-0.5 font-normal normal-case opacity-70">{a.due_date}</div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrixStudents.map((s) => (
                  <tr key={s.id} className="border-t border-border">
                    <td className="sticky left-0 bg-background px-4 py-3 font-medium whitespace-nowrap">
                      {s.first_name} {s.last_name_paternal}
                    </td>
                    {matrixActivities.map((a) => {
                      const key = scoreDraftKey(s.id, a.id);
                      return (
                        <td key={a.id} className="px-3 py-2">
                          <input
                            type="text"
                            inputMode="decimal"
                            aria-label={`Calificación ${s.first_name} ${s.last_name_paternal} — ${a.title}`}
                            data-score-key={key}
                            className={cellCls}
                            value={cellValue(s.id, a.id)}
                            onChange={(e) => setCellDraft(s.id, a.id, e.target.value)}
                          />
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      ) : termId === null ? (
        <p className="text-muted-foreground">Selecciona un periodo para ver las actividades.</p>
      ) : listQ.isLoading ? (
        <p className="text-muted-foreground">Cargando actividades…</p>
      ) : listQ.isError ? (
        <p className="text-destructive">No se pudieron cargar las actividades.</p>
      ) : activities.length === 0 ? (
        <p className="text-muted-foreground">No hay actividades en este periodo.</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border bg-card shadow-card">
          <div className="flex items-center justify-between px-5 py-4">
            <div>
              <h2 className="text-[15px] font-semibold">Actividades del periodo</h2>
              <p className="text-xs text-muted-foreground">Ordenadas por fecha de entrega</p>
            </div>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-left text-xs uppercase text-muted-foreground">
              <tr>
                <th className="px-4 py-3 font-medium">Actividad</th>
                <th className="px-4 py-3 font-medium">Tipo</th>
                <th className="px-4 py-3 font-medium">Entrega</th>
                <th className="px-4 py-3 font-medium">Campo</th>
              </tr>
            </thead>
            <tbody>
              {activities.map((a) => (
                <tr key={a.id} className="border-t border-border">
                  <td className="px-4 py-3 font-medium">{a.title}</td>
                  <td className="px-4 py-3">{TYPE_LABELS[a.type as TypeEnum] ?? a.type}</td>
                  <td className="px-4 py-3">{a.due_date}</td>
                  <td className="px-4 py-3">{a.field}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {open ? (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 pt-8"
          onClick={(e) => {
            if (e.target === e.currentTarget) close();
          }}
        >
          <Card
            role="dialog"
            aria-modal="true"
            aria-label="Nueva actividad"
            className="mx-4 flex w-full max-w-lg flex-col gap-4 bg-background p-6"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold">Nueva actividad</h2>
              <Button type="button" variant="ghost" size="icon-sm" onClick={close} aria-label="Cerrar">
                <X className="size-4" />
              </Button>
            </div>
            <FormField label="Título de la actividad" required>
              <input name="title" className={fieldCls} value={modal.title}
                onChange={(e) => setModal((p) => ({ ...p, title: e.target.value }))} />
            </FormField>
            <FormField label="Tipo" required>
              <Select name="type" value={modal.type}
                onChange={(e) => setModal((p) => ({ ...p, type: e.target.value as TypeEnum | "" }))}>
                <option value="">Selecciona tipo…</option>
                {(Object.keys(TYPE_LABELS) as TypeEnum[]).map((v) => (
                  <option key={v} value={v}>{TYPE_LABELS[v]}</option>
                ))}
              </Select>
            </FormField>
            <FormField label="Fecha de entrega" required>
              <input name="due_date" type="date" className={fieldCls} value={modal.due_date}
                onChange={(e) => setModal((p) => ({ ...p, due_date: e.target.value }))} />
            </FormField>
            <FormField label="Campo formativo" required>
              <Select name="field" value={modal.field}
                onChange={(e) => setModal((p) => ({ ...p, field: e.target.value, subject_ids: [] }))}>
                <option value="">Selecciona campo…</option>
                {(fieldsQ.data ?? []).map((f) => (
                  <option key={f.id} value={f.id}>{f.name}</option>
                ))}
              </Select>
            </FormField>
            <fieldset className="grid gap-2">
              <legend className="text-xs font-medium text-foreground/70">
                Asignaturas <span className="text-destructive">*</span>
              </legend>
              {modal.field === "" ? (
                <p className="text-xs text-muted-foreground">Elige un campo formativo primero.</p>
              ) : (
                subjects.map((s) => (
                  <label key={s.id} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      name="subject_ids"
                      value={s.id}
                      checked={modal.subject_ids.includes(s.id)}
                      onChange={() =>
                        setModal((p) => ({
                          ...p,
                          subject_ids: p.subject_ids.includes(s.id)
                            ? p.subject_ids.filter((id) => id !== s.id)
                            : [...p.subject_ids, s.id],
                        }))
                      }
                    />
                    {s.name}
                  </label>
                ))
              )}
            </fieldset>
            <FormField label="Descripción / instrucciones">
              <textarea name="description" rows={2}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={modal.description}
                onChange={(e) => setModal((p) => ({ ...p, description: e.target.value }))} />
            </FormField>
            {formError ? <p role="alert" className="text-sm text-destructive">{formError}</p> : null}
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={close}>Cancelar</Button>
              <Button type="button" onClick={submit} disabled={createM.isPending}>Crear actividad</Button>
            </div>
          </Card>
        </div>
      ) : null}
    </div>
  );
}
