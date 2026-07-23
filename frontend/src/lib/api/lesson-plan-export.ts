"use client";

import { MissingWorkspaceError } from "@/lib/api/client";
import { getActiveWorkspaceId } from "@/lib/workspace/store";

/**
 * Docx/md export download (ai-planeaciones spec — "Ready LessonPlan Can Be
 * Exported as Docx or Markdown"; design.md "Binary docx export fetched
 * outside the typed client"). `openapi-typescript`/`openapi-fetch` do not
 * model binary response bodies well, so this bypasses the generated
 * `client.ts` entirely and issues a plain credentialed `fetch`, reusing the
 * same `credentials: "include"` + `X-Workspace-Id` contract the middleware
 * applies to every other data request — GET is a "safe" method so no CSRF
 * token is needed here (mirrors `authMiddleware`'s own unsafe-method gate).
 */

const CONTENT_DISPOSITION_FILENAME = /filename="?([^";]+)"?/;

/** Pure helper: extracts the filename from a `Content-Disposition` header,
 * falling back to a caller-supplied default when the header is missing or
 * has no `filename` directive. */
export function filenameFromContentDisposition(
  header: string | null,
  fallback: string,
): string {
  if (!header) return fallback;
  const match = header.match(CONTENT_DISPOSITION_FILENAME);
  return match ? match[1] : fallback;
}

export async function downloadLessonPlanExport(
  id: number,
  format: "docx" | "md" = "docx",
): Promise<void> {
  const workspaceId = getActiveWorkspaceId();
  if (!workspaceId) throw new MissingWorkspaceError();

  const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const response = await fetch(
    `${baseUrl}/api/lesson-plans/${id}/export/?format=${format}`,
    {
      credentials: "include",
      headers: { "X-Workspace-Id": workspaceId },
    },
  );

  if (!response.ok) {
    throw new Error("No se pudo descargar la planeación.");
  }

  const blob = await response.blob();
  const filename = filenameFromContentDisposition(
    response.headers.get("Content-Disposition"),
    `planeacion-${id}.${format}`,
  );

  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
