/**
 * DRF error-body → human-readable message (frontend-foundation spec —
 * "Server-side validation error surfaces to the user"). DRF error bodies come
 * in two shapes from the school-structure endpoints:
 * - a plain array of strings, e.g. `ValidationError("msg")` raised by hand
 *   (the Group PROTECT-delete case in `schools/viewsets.py`)
 * - an object mapping field name -> array of message strings (default
 *   `ModelSerializer` field validation errors)
 */
export function extractErrorMessage(body: unknown): string {
  if (!body) return "Ocurrió un error. Inténtalo de nuevo.";

  if (Array.isArray(body)) {
    return body.map(String).join(" ");
  }

  if (typeof body === "object") {
    const parts = Object.entries(body as Record<string, unknown>).map(
      ([field, messages]) => {
        const text = Array.isArray(messages)
          ? messages.map(String).join(", ")
          : String(messages);
        return field === "non_field_errors" || field === "detail"
          ? text
          : `${field}: ${text}`;
      },
    );
    if (parts.length > 0) return parts.join(" ");
  }

  return "Ocurrió un error. Inténtalo de nuevo.";
}

/** Thrown by entity mutation/query hooks when the generated client returns a
 * non-2xx response, carrying the raw error body so callers can format it
 * with `extractErrorMessage`. */
export class ApiError extends Error {
  constructor(public readonly body: unknown) {
    super(extractErrorMessage(body));
    this.name = "ApiError";
  }
}
