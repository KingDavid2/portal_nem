/**
 * DEBUG Quizzy chat → Cursor Composer (POST /api/quizzy/chat/).
 * Raw fetch (not OpenAPI) because the route is a local-only stub.
 */

import { getActiveWorkspaceId } from "@/lib/workspace/store";
import { ApiError, extractErrorMessage } from "@/lib/api/errors";

export type QuizzyChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type QuizzyChatResponse = {
  reply: string;
  agent_id: string;
  model: string;
};

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

async function ensureCsrfToken(origin: string): Promise<string | null> {
  const existing = readCookie("csrftoken");
  if (existing) return existing;
  await fetch(`${origin}/api/auth/csrf/`, { credentials: "include" });
  return readCookie("csrftoken");
}

export async function postQuizzyChat(input: {
  message: string;
  agentId?: string | null;
}): Promise<QuizzyChatResponse> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const origin = new URL(baseUrl).origin;
  const workspaceId = getActiveWorkspaceId();
  if (!workspaceId) {
    throw new ApiError({ detail: "Selecciona un workspace antes de chatear." });
  }

  const csrf = await ensureCsrfToken(origin);
  const response = await fetch(`${origin}/api/quizzy/chat/`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(csrf ? { "X-CSRFToken": csrf } : {}),
      "X-Workspace-Id": workspaceId,
    },
    body: JSON.stringify({
      message: input.message,
      agent_id: input.agentId ?? null,
    }),
  });

  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(body ?? { detail: extractErrorMessage(body) });
  }
  return body as QuizzyChatResponse;
}
