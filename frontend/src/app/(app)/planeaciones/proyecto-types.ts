/**
 * TypeScript mirror of the backend's ABPC Pydantic schema
 * (`backend/lesson_plans/core/schema.py::Proyecto`), as it is stored/
 * serialized in `LessonPlan.proyecto` (a `JSONField` typed `unknown` in the
 * generated OpenAPI client — see `lesson-plans.ts`). Field names match
 * Pydantic's `model_dump()` output (snake_case) verbatim.
 */

export interface ProyectoDatos {
  school_name: string;
  cct: string;
  phase: number;
  grade: string;
  campo_formativo: string;
  methodology: string;
  date: string;
}

export interface ArticulatingAxis {
  name: string;
  justification: string;
}

export interface ContentPda {
  content: string;
  pdas: string[];
}

export interface ProyectoStep {
  number: number;
  dynamic: string;
}

export interface ProyectoSession {
  duration_minutes: number;
  steps: ProyectoStep[];
}

export interface ProyectoMomento {
  number: number;
  name: string;
  sessions: ProyectoSession[];
}

export interface ProyectoStage {
  name: string;
  momentos: ProyectoMomento[];
}

export interface RubricCriterion {
  criterion: string;
  levels: string[];
}

export interface Rubric {
  criteria: RubricCriterion[];
}

export interface Proyecto {
  datos: ProyectoDatos;
  title: string;
  purpose: string;
  articulating_axes: ArticulatingAxis[];
  problem_or_theme: string;
  contents_and_pdas: ContentPda[];
  stages: ProyectoStage[];
  rubric: Rubric;
}
