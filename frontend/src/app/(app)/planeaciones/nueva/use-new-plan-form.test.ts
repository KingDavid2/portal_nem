import { describe, expect, it } from "vitest";
import {
  buildCreatePayload,
  deriveEndDate,
  initialNewPlanForm,
  newPlanFormReducer,
  validateNewPlanForm,
  type NewPlanFormState,
} from "./use-new-plan-form";
import type { ContentSelection } from "./use-new-plan-form";

describe("initialNewPlanForm", () => {
  it("defaults every field for a null groupId", () => {
    expect(initialNewPlanForm(null)).toEqual({
      groupId: null,
      fieldId: "",
      subjectId: "",
      theme: "",
      contextDiagnosis: "",
      scenario: "community",
      durationWeeks: 3,
      startDate: "",
      endDate: "",
      endDateTouched: false,
      themeIds: [],
      selections: [],
    });
  });

  it("carries a numeric groupId through unchanged", () => {
    expect(initialNewPlanForm(42).groupId).toBe(42);
  });
});

describe("deriveEndDate", () => {
  it("adds durationWeeks * 7 - 1 days to startDate", () => {
    expect(deriveEndDate("2026-04-06", 3)).toBe("2026-04-26");
  });

  it("returns empty string for an empty startDate", () => {
    expect(deriveEndDate("", 3)).toBe("");
  });

  it("returns empty string for an invalid date", () => {
    expect(deriveEndDate("not-a-date", 3)).toBe("");
  });

  it("returns empty string for a zero duration", () => {
    expect(deriveEndDate("2026-04-06", 0)).toBe("");
  });

  it("returns empty string for a negative duration", () => {
    expect(deriveEndDate("2026-04-06", -1)).toBe("");
  });
});

function baseState(overrides: Partial<NewPlanFormState> = {}): NewPlanFormState {
  return { ...initialNewPlanForm(7), ...overrides };
}

describe("newPlanFormReducer", () => {
  it("recomputes endDate on setStartDate while untouched", () => {
    const state = baseState({ durationWeeks: 3 });
    const next = newPlanFormReducer(state, { type: "setStartDate", startDate: "2026-04-06" });
    expect(next.startDate).toBe("2026-04-06");
    expect(next.endDate).toBe("2026-04-26");
    expect(next.endDateTouched).toBe(false);
  });

  it("recomputes endDate on setDurationWeeks while untouched", () => {
    const state = baseState({ startDate: "2026-04-06", durationWeeks: 3 });
    const next = newPlanFormReducer(state, { type: "setDurationWeeks", durationWeeks: 4 });
    expect(next.durationWeeks).toBe(4);
    expect(next.endDate).toBe("2026-05-03");
  });

  it("does not recompute endDate after setEndDate has been dispatched", () => {
    const touched = newPlanFormReducer(baseState({ startDate: "2026-04-06", durationWeeks: 3 }), {
      type: "setEndDate",
      endDate: "2026-04-30",
    });
    expect(touched.endDateTouched).toBe(true);
    expect(touched.endDate).toBe("2026-04-30");

    const afterDuration = newPlanFormReducer(touched, {
      type: "setDurationWeeks",
      durationWeeks: 5,
    });
    expect(afterDuration.endDate).toBe("2026-04-30");

    const afterStart = newPlanFormReducer(afterDuration, {
      type: "setStartDate",
      startDate: "2026-05-01",
    });
    expect(afterStart.endDate).toBe("2026-04-30");
  });

  it("setField clears subjectId and selections but keeps themeIds", () => {
    const selections: ContentSelection[] = [{ content_id: "c1", pda_ids: ["p1"] }];
    const state = baseState({
      fieldId: "old-field",
      subjectId: "subj-1",
      selections,
      themeIds: ["theme-1"],
    });
    const next = newPlanFormReducer(state, { type: "setField", fieldId: "new-field" });
    expect(next.fieldId).toBe("new-field");
    expect(next.subjectId).toBe("");
    expect(next.selections).toEqual([]);
    expect(next.themeIds).toEqual(["theme-1"]);
  });

  it("toggleThemeId adds then removes an id", () => {
    const state = baseState({ themeIds: [] });
    const added = newPlanFormReducer(state, { type: "toggleThemeId", themeId: "t1" });
    expect(added.themeIds).toEqual(["t1"]);
    const removed = newPlanFormReducer(added, { type: "toggleThemeId", themeId: "t1" });
    expect(removed.themeIds).toEqual([]);
  });

  it("never mutates the input state object", () => {
    const state = baseState({ startDate: "2026-04-06", durationWeeks: 3 });
    const frozen = JSON.parse(JSON.stringify(state));
    newPlanFormReducer(state, { type: "setDurationWeeks", durationWeeks: 9 });
    expect(state).toEqual(frozen);
  });
});

function validState(overrides: Partial<NewPlanFormState> = {}): NewPlanFormState {
  return {
    groupId: 7,
    fieldId: "field-1",
    subjectId: "subject-1",
    theme: "Theme",
    contextDiagnosis: "Diagnosis",
    scenario: "community",
    durationWeeks: 3,
    startDate: "2026-04-06",
    endDate: "2026-04-26",
    endDateTouched: true,
    themeIds: ["theme-1"],
    selections: [{ content_id: "content-1", pda_ids: ["pda-1"] }],
    ...overrides,
  };
}

describe("validateNewPlanForm", () => {
  it("returns {} for a fully valid state", () => {
    expect(validateNewPlanForm(validState())).toEqual({});
  });

  it("requires groupId", () => {
    expect(validateNewPlanForm(validState({ groupId: null }))).toHaveProperty("groupId");
  });

  it("requires a non-empty fieldId", () => {
    const state = { ...validState(), fieldId: "   " };
    expect(validateNewPlanForm(state)).toHaveProperty("fieldId");
  });

  it("requires a non-empty theme", () => {
    const state = { ...validState(), theme: "   " };
    expect(validateNewPlanForm(state)).toHaveProperty("theme");
  });

  it("requires a non-empty contextDiagnosis", () => {
    const state = { ...validState(), contextDiagnosis: "" };
    expect(validateNewPlanForm(state)).toHaveProperty("contextDiagnosis");
  });

  it("rejects a durationWeeks below 1", () => {
    const state = { ...validState(), durationWeeks: 0 };
    expect(validateNewPlanForm(state)).toHaveProperty("durationWeeks");
  });

  it("rejects a durationWeeks above 12", () => {
    const state = { ...validState(), durationWeeks: 13 };
    expect(validateNewPlanForm(state)).toHaveProperty("durationWeeks");
  });

  it("rejects a non-integer durationWeeks", () => {
    const state = { ...validState(), durationWeeks: 2.5 };
    expect(validateNewPlanForm(state)).toHaveProperty("durationWeeks");
  });

  it("requires startDate", () => {
    const state = { ...validState(), startDate: "" };
    expect(validateNewPlanForm(state)).toHaveProperty("startDate");
  });

  it("requires endDate", () => {
    const state = { ...validState(), endDate: "" };
    expect(validateNewPlanForm(state)).toHaveProperty("endDate");
  });

  it("rejects an endDate before startDate", () => {
    const state = { ...validState(), startDate: "2026-04-10", endDate: "2026-04-01" };
    expect(validateNewPlanForm(state)).toHaveProperty("endDate");
  });

  it("requires at least one themeId", () => {
    const state = { ...validState(), themeIds: [] };
    expect(validateNewPlanForm(state)).toHaveProperty("themeIds");
  });

  it("requires at least one selection", () => {
    const state = { ...validState(), selections: [] };
    expect(validateNewPlanForm(state)).toHaveProperty("selections");
  });

  it("requires every selection to have at least one pda_id", () => {
    const state = { ...validState(), selections: [{ content_id: "c1", pda_ids: [] }] };
    expect(validateNewPlanForm(state)).toHaveProperty("selections");
  });
});

describe("buildCreatePayload", () => {
  it("returns null for an invalid state", () => {
    const state = { ...validState(), theme: "" };
    expect(buildCreatePayload(state, "methodology-1")).toBeNull();
  });

  it("returns null for an empty methodologyId", () => {
    expect(buildCreatePayload(validState(), "")).toBeNull();
  });

  it("returns the exact create body for a valid state", () => {
    const state = validState();
    const payload = buildCreatePayload(state, "methodology-1");
    expect(payload).toEqual({
      group: 7,
      field_id: "field-1",
      subject_id: "subject-1",
      methodology_id: "methodology-1",
      theme: "Theme",
      context_diagnosis: "Diagnosis",
      scenario: "community",
      duration_weeks: 3,
      start_date: "2026-04-06",
      end_date: "2026-04-26",
      cross_cutting_theme_ids: ["theme-1"],
      content_selections: [{ content_id: "content-1", pda_ids: ["pda-1"] }],
    });
  });

  it("copies arrays so the caller cannot mutate form state through the payload", () => {
    const state = validState();
    const payload = buildCreatePayload(state, "methodology-1");
    expect(payload).not.toBeNull();
    if (!payload) return;
    payload.cross_cutting_theme_ids.push("mutated");
    payload.content_selections[0]!.pda_ids.push("mutated");
    expect(state.themeIds).toEqual(["theme-1"]);
    expect(state.selections[0]!.pda_ids).toEqual(["pda-1"]);
  });
});
