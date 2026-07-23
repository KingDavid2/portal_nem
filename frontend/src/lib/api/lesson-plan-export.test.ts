import { beforeEach, describe, expect, it, vi } from "vitest";

/**
 * Focused unit tests for the docx/md export download helper (ai-planeaciones
 * spec — "Ready LessonPlan Can Be Exported as Docx or Markdown"; design.md
 * "Binary docx export fetched outside the typed client"; tasks.md D8.2/8.4
 * `npm test -- viewer`). Downloads a binary body via a plain credentialed
 * `fetch` + `Blob` anchor — not the typed `openapi-fetch` client, which
 * cannot model binary bodies — reusing the client's credentials + CSRF +
 * `X-Workspace-Id` contract.
 */

let activeWorkspaceId: string | null = "workspace-1";

vi.mock("@/lib/workspace/store", () => ({
  getActiveWorkspaceId: () => activeWorkspaceId,
}));

const { downloadLessonPlanExport, filenameFromContentDisposition } = await import(
  "./lesson-plan-export"
);
const { MissingWorkspaceError } = await import("./client");

describe("filenameFromContentDisposition", () => {
  it("extracts the filename from a Content-Disposition header", () => {
    expect(
      filenameFromContentDisposition(
        'attachment; filename="la-independencia.docx"',
        "fallback.docx",
      ),
    ).toBe("la-independencia.docx");
  });

  it("falls back when the header is missing", () => {
    expect(filenameFromContentDisposition(null, "fallback.docx")).toBe("fallback.docx");
  });

  it("falls back when the header has no filename directive", () => {
    expect(filenameFromContentDisposition("attachment", "fallback.docx")).toBe(
      "fallback.docx",
    );
  });
});

describe("downloadLessonPlanExport", () => {
  beforeEach(() => {
    activeWorkspaceId = "workspace-1";
    vi.restoreAllMocks();
  });

  it("refuses to download when no workspace is active", async () => {
    activeWorkspaceId = null;
    await expect(downloadLessonPlanExport(1, "docx")).rejects.toBeInstanceOf(
      MissingWorkspaceError,
    );
  });

  it("fetches the export endpoint with credentials + X-Workspace-Id and triggers a download", async () => {
    const blob = new Blob(["binary-content"]);
    const headers = new Headers({
      "Content-Disposition": 'attachment; filename="la-independencia.docx"',
    });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(blob, { status: 200, headers }),
    );
    const createObjectUrlSpy = vi
      .spyOn(URL, "createObjectURL")
      .mockReturnValue("blob:mock-url");
    const revokeObjectUrlSpy = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
    const clickSpy = vi.fn();
    const originalCreateElement = document.createElement.bind(document);
    const createElementSpy = vi
      .spyOn(document, "createElement")
      .mockImplementation((tag: string) => {
        const el = originalCreateElement(tag);
        el.click = clickSpy;
        return el;
      });

    await downloadLessonPlanExport(42, "docx");

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/api/lesson-plans/42/export/?format=docx"),
      expect.objectContaining({
        credentials: "include",
        headers: expect.objectContaining({ "X-Workspace-Id": "workspace-1" }),
      }),
    );
    expect(clickSpy).toHaveBeenCalled();
    expect(createObjectUrlSpy).toHaveBeenCalled();
    expect(revokeObjectUrlSpy).toHaveBeenCalledWith("blob:mock-url");

    createElementSpy.mockRestore();
  });

  it("throws when the response is not ok", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 404 }));
    await expect(downloadLessonPlanExport(1, "docx")).rejects.toThrow();
  });
});
