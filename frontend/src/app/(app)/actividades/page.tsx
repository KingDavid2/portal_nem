"use client";

import { useMemo, useState } from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ChoiceChip } from "@/components/ui/choice-chip";
import { FormField } from "@/components/ui/form-field";
import { Select } from "@/components/ui/select";
import {
  useActivitiesQuery,
  useCreateActivityMutation,
  type ActivityCreate,
  type Term,
  type TypeEnum,
} from "@/lib/api/grades";
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

/** Por actividad list + Nueva modal. Por alumno matrix lands in D4. */
export default function ActividadesPage() {
  const { groupId, setGroupId, visibleGroups } = useSchoolTeachingContext();
  const [view, setView] = useState<ViewMode>("by-activity");
  const [termId, setTermId] = useState<number | null>(null);
  const [open, setOpen] = useState(false);
  const [modal, setModal] = useState<ModalDraft>(EMPTY);
  const [formError, setFormError] = useState<string | null>(null);

  const listQ = useActivitiesQuery(groupId, termId);
  const createM = useCreateActivityMutation();
  const fieldsQ = useLessonPlanFieldsQuery();
  const catalogQ = useLessonPlanCatalogQuery(groupId, open ? modal.field : "");

  const terms = listQ.data?.terms ?? FALLBACK_TERMS;
  const activities = termId === null ? [] : (listQ.data?.activities ?? []);
  const subjects = catalogQ.data?.subjects ?? [];
  const groups = useMemo(
    () => visibleGroups.map((g) => ({ id: g.id, label: `${g.grado} ${g.grupo}` })),
    [visibleGroups],
  );

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
      </header>

      <div className="grid gap-4 rounded-xl bg-card p-5 shadow-card md:grid-cols-2">
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
        <FormField label="Periodo" required>
          <Select
            name="termId"
            aria-label="Periodo"
            value={termId ?? ""}
            onChange={(e) => setTermId(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">Selecciona un periodo…</option>
            {terms.map((t) => (
              <option key={t.id} value={t.id}>Periodo {t.number}</option>
            ))}
          </Select>
        </FormField>
      </div>

      {view === "by-student" ? (
        <p className="text-muted-foreground">Vista Por alumno — matriz en la siguiente entrega.</p>
      ) : termId === null ? (
        <p className="text-muted-foreground">Selecciona un periodo para ver las actividades.</p>
      ) : listQ.isLoading ? (
        <p className="text-muted-foreground">Cargando actividades…</p>
      ) : listQ.isError ? (
        <p className="text-destructive">No se pudieron cargar las actividades.</p>
      ) : activities.length === 0 ? (
        <p className="text-muted-foreground">No hay actividades en este periodo.</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border">
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
