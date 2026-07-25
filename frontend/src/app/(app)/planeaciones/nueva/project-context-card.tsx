import type { NewPlanFormState, NewPlanFormAction, ScenarioEnum } from "./use-new-plan-form";
import type { Group } from "@/lib/api/groups";
import type { CatalogField, LessonPlanCatalog } from "@/lib/api/lesson-plan-catalog";
import { Card } from "@/components/ui/card";
import { FormField } from "@/components/ui/form-field";
import { Select } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { ChoiceChip } from "@/components/ui/choice-chip";

type Props = {
  state: NewPlanFormState;
  dispatch: React.Dispatch<NewPlanFormAction>;
  groups: Group[];
  fields: CatalogField[];
  catalog: LessonPlanCatalog | undefined;
};

/** Geometry shared by every box in this card. `Input` ships at `h-8`/
 * `rounded-lg` while `Select` is pinned to the Pencil design's `h-10`/
 * `rounded-md`, so the text and date inputs are pulled up to the taller box
 * here — otherwise rows 1-3 would step between two heights inside one card.
 * The same reasoning is written out in `components/ui/select.tsx`. */
const BOX_GEOMETRY = "h-10 rounded-md";

/** Read-only boxes (Metodología, Fase, Grado) are not disabled controls: their
 * values are derived server-side and there is nothing for the teacher to
 * operate. Rendering them as plain divs at the same geometry keeps the grid
 * aligned without lying to assistive tech about a control that does not exist. */
const READ_ONLY_BOX = `${BOX_GEOMETRY} flex w-full min-w-0 items-center border border-input bg-card px-3 text-sm text-foreground/70`;

/** Escenario is a mutually exclusive set, but `ChoiceChip` owns no group and so
 * reports the *toggled* value — an already-selected chip would report `false`.
 * These call sites therefore ignore the callback argument and set their own id,
 * exactly as the primitive's JSDoc prescribes. */
const SCENARIOS: { id: ScenarioEnum; label: string }[] = [
  { id: "classroom", label: "Aula" },
  { id: "school", label: "Escuela" },
  { id: "community", label: "Comunidad" },
];

/** Card 1 of the Nueva planeación screen: everything the teacher decides about
 * the project before choosing ejes and contenidos. Purely presentational — it
 * owns no state, dispatching every change into the reducer in
 * `use-new-plan-form.ts` so the cross-field rules stay testable without a DOM. */
export function ProjectContextCard({ state, dispatch, groups, fields, catalog }: Props) {
  return (
    <Card className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h2 className="text-base font-semibold">Contexto del proyecto</h2>
        <p className="text-[13px] text-muted-foreground">
          Estos datos alimentan la generación. Entre más específico el diagnóstico, más
          contextualizado el proyecto.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <FormField label="Grupo" required>
          <Select
            name="groupId"
            value={state.groupId ?? ""}
            onChange={(event) =>
              dispatch({
                type: "setGroup",
                groupId: event.target.value ? Number(event.target.value) : null,
              })
            }
          >
            <option value="">Selecciona un grupo…</option>
            {groups.map((group) => (
              <option key={group.id} value={group.id}>
                {group.grado}° {group.grupo}
              </option>
            ))}
          </Select>
        </FormField>

        <FormField label="Campo formativo" required>
          <Select
            name="fieldId"
            value={state.fieldId}
            onChange={(event) => dispatch({ type: "setField", fieldId: event.target.value })}
          >
            <option value="">Selecciona un campo…</option>
            {fields.map((field) => (
              <option key={field.id} value={field.id}>
                {field.name}
              </option>
            ))}
          </Select>
        </FormField>

        <FormField label="Metodología" required>
          <div className={READ_ONLY_BOX}>{catalog?.methodology.name ?? "—"}</div>
        </FormField>

        <FormField label="Fase" help="Derivada del grupo">
          <div className={READ_ONLY_BOX}>{catalog ? `Fase ${catalog.phase}` : "—"}</div>
        </FormField>

        <FormField label="Grado" help="Derivado del grupo">
          <div className={READ_ONLY_BOX}>{catalog ? `${catalog.grade}°` : "—"}</div>
        </FormField>

        <FormField label="Materia" help="Solo aplica en Fase 6">
          <Select
            name="subjectId"
            value={state.subjectId}
            disabled={catalog === undefined}
            onChange={(event) => dispatch({ type: "setSubject", subjectId: event.target.value })}
          >
            <option value="">Selecciona una materia…</option>
            {catalog?.subjects.map((subject) => (
              <option key={subject.id} value={subject.id}>
                {subject.name}
              </option>
            ))}
          </Select>
        </FormField>

        <FormField label="Duración">
          <Input
            name="durationWeeks"
            type="number"
            min={1}
            max={12}
            className={BOX_GEOMETRY}
            value={state.durationWeeks}
            onChange={(event) =>
              dispatch({ type: "setDurationWeeks", durationWeeks: Number(event.target.value) })
            }
          />
        </FormField>

        <FormField label="Fecha de inicio">
          <Input
            name="startDate"
            type="date"
            className={BOX_GEOMETRY}
            value={state.startDate}
            onChange={(event) => dispatch({ type: "setStartDate", startDate: event.target.value })}
          />
        </FormField>

        <FormField label="Fecha de cierre">
          <Input
            name="endDate"
            type="date"
            className={BOX_GEOMETRY}
            value={state.endDate}
            onChange={(event) => dispatch({ type: "setEndDate", endDate: event.target.value })}
          />
        </FormField>
      </div>

      <FormField label="Tema o problemática" required>
        <Input
          name="theme"
          className={BOX_GEOMETRY}
          value={state.theme}
          onChange={(event) => dispatch({ type: "setTheme", theme: event.target.value })}
        />
      </FormField>

      <FormField label="Contexto / diagnóstico socioeducativo" required>
        {/* Local styling rather than a primitive: this is the only textarea in
            the app, so extracting one now would be speculative. The classes
            mirror `select.tsx` so the box reads as part of the same set. */}
        <textarea
          name="contextDiagnosis"
          rows={4}
          className="w-full min-w-0 rounded-md border border-input bg-card px-3 py-2 text-sm transition-colors outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
          value={state.contextDiagnosis}
          onChange={(event) =>
            dispatch({ type: "setContextDiagnosis", contextDiagnosis: event.target.value })
          }
        />
      </FormField>

      <div className="flex flex-col gap-2">
        <span className="text-xs font-medium text-foreground/70">Escenario</span>
        <div className="flex flex-wrap gap-2">
          {SCENARIOS.map(({ id, label }) => (
            <ChoiceChip
              key={id}
              variant="single"
              selected={state.scenario === id}
              onSelectedChange={() => dispatch({ type: "setScenario", scenario: id })}
            >
              {label}
            </ChoiceChip>
          ))}
        </div>
      </div>
    </Card>
  );
}
