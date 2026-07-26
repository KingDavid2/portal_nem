import { describe, expect, it } from "vitest";
import {
  demoSessionPollInterval,
  readDemoModeFlag,
  type DemoSession,
} from "@/lib/api/demo";

/**
 * Focused unit tests for the demo session polling interval resolver
 * (M5 Demo mode — "Client polls until provisioning completes").
 * Mirrors `lessonPlanPollInterval` conventions from `lesson-plans.test.ts`.
 */

function session(overrides: Partial<DemoSession>): DemoSession {
  return {
    id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    persona: "teacher_minimal",
    status: "pending",
    workspace: null,
    email: null,
    error_message: "",
    ...overrides,
  };
}

describe("demoSessionPollInterval", () => {
  it("keeps polling while the session is undefined (still loading the first response)", () => {
    expect(demoSessionPollInterval(undefined)).toBe(2000);
  });

  it("keeps polling while status is pending", () => {
    expect(demoSessionPollInterval(session({ status: "pending" }))).toBe(2000);
  });

  it("stops polling once status is ready", () => {
    expect(demoSessionPollInterval(session({ status: "ready" }))).toBe(false);
  });

  it("stops polling once status is failed", () => {
    expect(demoSessionPollInterval(session({ status: "failed" }))).toBe(false);
  });
});

describe("readDemoModeFlag", () => {
  it("reports demo mode on only for a literal true flag", () => {
    expect(readDemoModeFlag({ status: "ok", demo_mode: true })).toBe(true);
  });

  it("reports demo mode off when the flag is false", () => {
    expect(readDemoModeFlag({ status: "ok", demo_mode: false })).toBe(false);
  });

  it("reports demo mode off when the flag is missing", () => {
    expect(readDemoModeFlag({ status: "ok", version: "1.0" })).toBe(false);
  });

  it("reports demo mode off for truthy non-boolean flags and non-objects", () => {
    expect(readDemoModeFlag({ demo_mode: "true" })).toBe(false);
    expect(readDemoModeFlag({ demo_mode: 1 })).toBe(false);
    expect(readDemoModeFlag(null)).toBe(false);
    expect(readDemoModeFlag(undefined)).toBe(false);
  });
});