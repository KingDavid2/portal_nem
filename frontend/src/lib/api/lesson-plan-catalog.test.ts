import { describe, expect, it } from "vitest";
import {
  catalogQueryEnabled,
  generationQuotaQueryKey,
  lessonPlanCatalogQueryKey,
  lessonPlanFieldsQueryKey,
} from "@/lib/api/lesson-plan-catalog";

/**
 * Focused unit tests for the lesson-plan catalog's pure gating helper and
 * query key shapes (ai-planeaciones spec). `catalogQueryEnabled` is the pure
 * resolver behind `useLessonPlanCatalogQuery`'s `enabled` option — mirroring
 * `lessonPlanPollInterval` in `lesson-plans.ts`, it is kept pure so the
 * gating contract (group AND field both required) is unit-testable without a
 * network.
 */

describe("catalogQueryEnabled", () => {
  it("is false when no group is selected and no field is selected", () => {
    expect(catalogQueryEnabled(null, "")).toBe(false);
  });

  it("is false when no group is selected but a field is selected", () => {
    expect(catalogQueryEnabled(null, "languages")).toBe(false);
  });

  it("is false when a group is selected but the field is an empty string", () => {
    expect(catalogQueryEnabled(10, "")).toBe(false);
  });

  it("is false when a group is selected but the field is whitespace-only", () => {
    expect(catalogQueryEnabled(10, "   ")).toBe(false);
  });

  it("is true when both a group and a field are selected", () => {
    expect(catalogQueryEnabled(10, "languages")).toBe(true);
  });
});

describe("query keys", () => {
  it("lessonPlanFieldsQueryKey is a fixed tuple", () => {
    expect(lessonPlanFieldsQueryKey).toEqual(["lesson-plan-fields"]);
  });

  it("generationQuotaQueryKey is a fixed tuple", () => {
    expect(generationQuotaQueryKey).toEqual(["generation-quota"]);
  });

  it("lessonPlanCatalogQueryKey varies by group and field", () => {
    expect(lessonPlanCatalogQueryKey(10, "languages")).toEqual([
      "lesson-plan-catalog",
      10,
      "languages",
    ]);
    expect(lessonPlanCatalogQueryKey(20, "languages")).toEqual([
      "lesson-plan-catalog",
      20,
      "languages",
    ]);
    expect(lessonPlanCatalogQueryKey(10, "math")).toEqual([
      "lesson-plan-catalog",
      10,
      "math",
    ]);
  });
});
