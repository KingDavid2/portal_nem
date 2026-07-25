import { useReducer } from "react";
import type { components } from "@/lib/api/schema";
import type { LessonPlanInput } from "@/lib/api/lesson-plans";

/**
 * Pure form state for the "Nueva planeación" wizard, kept in a plain
 * reducer instead of scattered `useState` calls so the derived-field rule
 * (start date / duration drive a default end date, until the teacher
 * overrides it) and the create-payload shape live in one place that a test
 * can exercise without rendering anything.
 */

export type ScenarioEnum = components["schemas"]["ScenarioEnum"];
export type ContentSelection = components["schemas"]["ContentSelection"];

export type NewPlanFormState = {
  groupId: number | null;
  fieldId: string;
  subjectId: string;
  theme: string;
  contextDiagnosis: string;
  scenario: ScenarioEnum;
  durationWeeks: number;
  startDate: string;
  endDate: string;
  endDateTouched: boolean;
  themeIds: string[];
  selections: ContentSelection[];
};

export type NewPlanFormAction =
  | { type: "setGroup"; groupId: number | null }
  | { type: "setField"; fieldId: string }
  | { type: "setSubject"; subjectId: string }
  | { type: "setTheme"; theme: string }
  | { type: "setContextDiagnosis"; contextDiagnosis: string }
  | { type: "setScenario"; scenario: ScenarioEnum }
  | { type: "setDurationWeeks"; durationWeeks: number }
  | { type: "setStartDate"; startDate: string }
  | { type: "setEndDate"; endDate: string }
  | { type: "toggleThemeId"; themeId: string }
  | { type: "setSelections"; selections: ContentSelection[] };

const DEFAULT_SCENARIO: ScenarioEnum = "community";
const DEFAULT_DURATION_WEEKS = 3;

/** Builds the form's day-one state: a form the teacher has not touched yet,
 * scoped to whichever group was active when she opened the page. */
export function initialNewPlanForm(groupId: number | null): NewPlanFormState {
  return {
    groupId,
    fieldId: "",
    subjectId: "",
    theme: "",
    contextDiagnosis: "",
    scenario: DEFAULT_SCENARIO,
    durationWeeks: DEFAULT_DURATION_WEEKS,
    startDate: "",
    endDate: "",
    endDateTouched: false,
    themeIds: [],
    selections: [],
  };
}

const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

/** Convenience default for `endDate`: a project that runs `durationWeeks`
 * inclusive of both its start and end day. Returns `""` on any input that
 * cannot support the arithmetic (blank/invalid start date, non-positive
 * duration) so callers can treat an empty result as "no default available"
 * rather than special-casing the inputs themselves. Uses UTC arithmetic so
 * the caller's local timezone can never shift the computed day. */
export function deriveEndDate(startDate: string, durationWeeks: number): string {
  if (!ISO_DATE_PATTERN.test(startDate)) return "";
  if (!Number.isInteger(durationWeeks) || durationWeeks <= 0) return "";

  const [year, month, day] = startDate.split("-").map(Number) as [number, number, number];
  const start = Date.UTC(year, month - 1, day);
  if (Number.isNaN(start)) return "";
  // Guard against non-existent calendar dates (e.g. 2026-02-30) round-tripping silently.
  const startAsDate = new Date(start);
  if (
    startAsDate.getUTCFullYear() !== year ||
    startAsDate.getUTCMonth() !== month - 1 ||
    startAsDate.getUTCDate() !== day
  ) {
    return "";
  }

  const end = new Date(start);
  end.setUTCDate(end.getUTCDate() + durationWeeks * 7 - 1);
  return end.toISOString().slice(0, 10);
}

/** Recomputes `endDate` from the state's current `startDate`/`durationWeeks`,
 * but only until the teacher has picked her own closing date — the default
 * is a convenience, never a constraint the reducer re-imposes afterward. */
function withDerivedEndDate(state: NewPlanFormState): NewPlanFormState {
  if (state.endDateTouched) return state;
  return { ...state, endDate: deriveEndDate(state.startDate, state.durationWeeks) };
}

/** The form's reducer. One action per field plus the two derivation points
 * (`setStartDate`, `setDurationWeeks`) that keep `endDate` in sync until the
 * teacher overrides it via `setEndDate`. Every branch returns a fresh
 * object — the caller never has to guard against in-place mutation. */
export function newPlanFormReducer(
  state: NewPlanFormState,
  action: NewPlanFormAction,
): NewPlanFormState {
  switch (action.type) {
    case "setGroup":
      return { ...state, groupId: action.groupId };
    case "setField":
      // fieldId scopes both subjectId and content selections in the catalog;
      // themeIds are cross-cutting themes, which are field-independent.
      return { ...state, fieldId: action.fieldId, subjectId: "", selections: [] };
    case "setSubject":
      return { ...state, subjectId: action.subjectId };
    case "setTheme":
      return { ...state, theme: action.theme };
    case "setContextDiagnosis":
      return { ...state, contextDiagnosis: action.contextDiagnosis };
    case "setScenario":
      return { ...state, scenario: action.scenario };
    case "setDurationWeeks":
      return withDerivedEndDate({ ...state, durationWeeks: action.durationWeeks });
    case "setStartDate":
      return withDerivedEndDate({ ...state, startDate: action.startDate });
    case "setEndDate":
      return { ...state, endDate: action.endDate, endDateTouched: true };
    case "toggleThemeId":
      return {
        ...state,
        themeIds: state.themeIds.includes(action.themeId)
          ? state.themeIds.filter((id) => id !== action.themeId)
          : [...state.themeIds, action.themeId],
      };
    case "setSelections":
      return { ...state, selections: action.selections };
    default: {
      const exhaustive: never = action;
      return exhaustive;
    }
  }
}

/** Wraps `newPlanFormReducer`/`initialNewPlanForm` in `useReducer` — the one
 * spot in this module allowed to touch React, so every other export stays a
 * plain function a unit test can call directly. */
export function useNewPlanForm(groupId: number | null) {
  return useReducer(newPlanFormReducer, groupId, initialNewPlanForm);
}

const DURATION_WEEKS_MIN = 1;
const DURATION_WEEKS_MAX = 12;

/** Mirrors the write-boundary checks the backend enforces in
 * `lesson_plans/validation.py` — required fields, the 1-12 week duration
 * window, `endDate >= startDate`, and non-empty theme/selection lists —
 * so the wizard can reject an incomplete submission before it ever reaches
 * the network. Messages are short, teacher-facing Spanish; error keys match
 * the state field they describe. */
export function validateNewPlanForm(state: NewPlanFormState): Record<string, string> {
  const errors: Record<string, string> = {};

  if (state.groupId === null) {
    errors.groupId = "Selecciona un grupo.";
  }
  if (state.fieldId.trim() === "") {
    errors.fieldId = "Selecciona un campo formativo.";
  }
  if (state.theme.trim() === "") {
    errors.theme = "Escribe el tema del proyecto.";
  }
  if (state.contextDiagnosis.trim() === "") {
    errors.contextDiagnosis = "Escribe el diagnóstico de contexto.";
  }
  if (
    !Number.isInteger(state.durationWeeks) ||
    state.durationWeeks < DURATION_WEEKS_MIN ||
    state.durationWeeks > DURATION_WEEKS_MAX
  ) {
    errors.durationWeeks = "La duración debe ser de 1 a 12 semanas.";
  }
  if (state.startDate === "") {
    errors.startDate = "Selecciona la fecha de inicio.";
  }
  if (state.endDate === "") {
    errors.endDate = "Selecciona la fecha de cierre.";
  } else if (state.startDate !== "" && state.endDate < state.startDate) {
    errors.endDate = "La fecha de cierre no puede ser anterior al inicio.";
  }
  if (state.themeIds.length === 0) {
    errors.themeIds = "Selecciona al menos una transversalidad.";
  }
  if (state.selections.length === 0) {
    errors.selections = "Selecciona al menos un contenido.";
  } else if (state.selections.some((selection) => selection.pda_ids.length === 0)) {
    errors.selections = "Cada contenido debe tener al menos un PDA.";
  }

  return errors;
}

/** Builds the `POST /api/lesson-plans/` body from form state, or `null` when
 * the form is not submittable yet (validation errors, or no methodology
 * chosen). Arrays are copied so the payload can be handed off to a mutation
 * without the caller being able to mutate live form state through it — and
 * the object is built key-by-key so a stray `campo`/`grade` (fields the
 * server derives and rejects) can never sneak in. */
export function buildCreatePayload(
  state: NewPlanFormState,
  methodologyId: string,
): LessonPlanInput | null {
  if (methodologyId === "") return null;
  if (Object.keys(validateNewPlanForm(state)).length > 0) return null;

  return {
    group: state.groupId as number,
    field_id: state.fieldId,
    subject_id: state.subjectId,
    methodology_id: methodologyId,
    theme: state.theme.trim(),
    context_diagnosis: state.contextDiagnosis.trim(),
    scenario: state.scenario,
    duration_weeks: state.durationWeeks,
    start_date: state.startDate,
    end_date: state.endDate,
    cross_cutting_theme_ids: [...state.themeIds],
    content_selections: state.selections.map((selection) => ({
      content_id: selection.content_id,
      pda_ids: [...selection.pda_ids],
    })),
  };
}
