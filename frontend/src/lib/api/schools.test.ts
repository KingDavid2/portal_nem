import { describe, expect, it } from "vitest";
import { ApiError, extractErrorMessage } from "@/lib/api/errors";

/**
 * Focused unit tests for the DRF error-body → message extraction shared by
 * every school-structure entity screen (frontend-foundation spec —
 * "Server-side validation error surfaces to the user"; tasks.md D7
 * `npm test -- school`).
 */
describe("extractErrorMessage", () => {
  it("joins a plain array of strings (e.g. Group PROTECT-delete ValidationError)", () => {
    expect(
      extractErrorMessage(["Cannot delete a group that still has students assigned to it."]),
    ).toBe("Cannot delete a group that still has students assigned to it.");
  });

  it("formats field -> messages objects (default ModelSerializer validation errors)", () => {
    expect(extractErrorMessage({ name: ["This field is required."] })).toBe(
      "name: This field is required.",
    );
  });

  it("formats non_field_errors without the field-name prefix", () => {
    expect(
      extractErrorMessage({
        non_field_errors: ["The fields school, label must make a unique set."],
      }),
    ).toBe("The fields school, label must make a unique set.");
  });

  it("falls back to a generic message for empty/unknown bodies", () => {
    expect(extractErrorMessage(null)).toBe("Ocurrió un error. Inténtalo de nuevo.");
    expect(extractErrorMessage(undefined)).toBe("Ocurrió un error. Inténtalo de nuevo.");
  });
});

describe("ApiError", () => {
  it("carries the raw body and derives its message via extractErrorMessage", () => {
    const error = new ApiError({ cct: ["Ensure this field has no more than 10 characters."] });
    expect(error.message).toBe("cct: Ensure this field has no more than 10 characters.");
    expect(error.body).toEqual({ cct: ["Ensure this field has no more than 10 characters."] });
  });
});
