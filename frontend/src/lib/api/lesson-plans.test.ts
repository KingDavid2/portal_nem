import { describe, expect, it } from "vitest";
import {
  lessonPlanCreateInput,
  lessonPlanPollInterval,
  lessonPlansForGroup,
  type LessonPlan,
} from "@/lib/api/lesson-plans";

/**
 * Focused unit tests for the LessonPlan client-side group scoping helper and
 * the async-poll interval resolver (ai-planeaciones spec — "CRUD Endpoints
 * Are Workspace-Scoped", "Generation Runs Asynchronously via a Celery Task";
 * tasks.md D7.5 `npm test -- planeaciones`). `/api/lesson-plans/` has no
 * server-side `?group=` typed in the generated client (undocumented query
 * param), so — mirroring `groupsForSchoolYear`/`studentsForGroup` — the
 * screen fetches every plan in the workspace and scopes it client-side.
 */

function plan(overrides: Partial<LessonPlan>): LessonPlan {
  return {
    id: 1,
    workspace: "ws-1",
    group: 10,
    campo: "Lenguajes",
    grade: "6",
    theme: "La independencia",
    field_id: "languages",
    subject_id: "spanish",
    methodology_id: "community-based-project-learning",
    duration_weeks: 4,
    start_date: "2026-01-12",
    end_date: "2026-02-06",
    scenario: "community",
    context_diagnosis: "El grupo requiere fortalecer la producción escrita.",
    cross_cutting_theme_ids: ["critical-thinking"],
    content_selections: [
      { content_id: "languages-text-resources", pda_ids: ["languages-accentuation"] },
    ],
    title: "",
    proyecto: null,
    status: "pending",
    failure_reason: "",
    provider: "",
    model_name: "",
    prompt_tokens: null,
    completion_tokens: null,
    invented_pdas: false,
    invented_pda_texts: [],
    grounding_selections: [],
    generated_at: null,
    created_at: "2026-07-01T00:00:00Z",
    ...overrides,
  };
}

describe("lessonPlansForGroup", () => {
  it("returns only plans belonging to the given group id", () => {
    const plans = [
      plan({ id: 1, group: 10 }),
      plan({ id: 2, group: 20 }),
      plan({ id: 3, group: 10 }),
    ];
    expect(lessonPlansForGroup(plans, 10)).toEqual([plans[0], plans[2]]);
  });

  it("returns an empty list when no group is selected", () => {
    expect(lessonPlansForGroup([plan({})], null)).toEqual([]);
  });

  it("returns an empty list when the group id has no matching rows", () => {
    expect(lessonPlansForGroup([plan({ group: 10 })], 999)).toEqual([]);
  });
});

describe("lessonPlanCreateInput", () => {
  it("rebuilds the create body from the persisted project context", () => {
    expect(lessonPlanCreateInput(plan({ group: 12 }))).toEqual({
      group: 12,
      field_id: "languages",
      subject_id: "spanish",
      methodology_id: "community-based-project-learning",
      theme: "La independencia",
      context_diagnosis: "El grupo requiere fortalecer la producción escrita.",
      scenario: "community",
      duration_weeks: 4,
      start_date: "2026-01-12",
      end_date: "2026-02-06",
      cross_cutting_theme_ids: ["critical-thinking"],
      content_selections: [
        { content_id: "languages-text-resources", pda_ids: ["languages-accentuation"] },
      ],
    });
  });

  it.each(["duration_weeks", "start_date", "end_date"] as const)(
    "returns null when %s was never persisted",
    (field) => {
      expect(lessonPlanCreateInput(plan({ [field]: null }))).toBeNull();
    },
  );

  it("returns null when the plan predates the catalog contract", () => {
    expect(lessonPlanCreateInput(plan({ field_id: "" }))).toBeNull();
  });
});

describe("lessonPlanPollInterval", () => {
  it("keeps polling while the plan is undefined (still loading the first response)", () => {
    expect(lessonPlanPollInterval(undefined)).toBe(3000);
  });

  it("keeps polling while status is pending", () => {
    expect(lessonPlanPollInterval(plan({ status: "pending" }))).toBe(3000);
  });

  it("stops polling once status is ready", () => {
    expect(lessonPlanPollInterval(plan({ status: "ready" }))).toBe(false);
  });

  it("stops polling once status is failed", () => {
    expect(lessonPlanPollInterval(plan({ status: "failed" }))).toBe(false);
  });
});
