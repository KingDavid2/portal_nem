/**
 * Quizzy chat + conversation history (POST/GET/DELETE).
 * Raw fetch (not OpenAPI) — local Composer stub surface.
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
  conversation_id: string;
};

export type QuizzyConversationSummary = {
  id: string;
  title: string;
  agent_id: string;
  created_at: string;
  updated_at: string;
};

export type QuizzyConversationDetail = QuizzyConversationSummary & {
  messages: Array<{
    id: string;
    role: "user" | "assistant";
    content: string;
    created_at: string;
  }>;
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

function apiOrigin(): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  return new URL(baseUrl).origin;
}

async function quizzyFetch(
  path: string,
  init: RequestInit & { json?: unknown } = {},
): Promise<Response> {
  const origin = apiOrigin();
  const workspaceId = getActiveWorkspaceId();
  if (!workspaceId) {
    throw new ApiError({
      detail: "Selecciona un workspace antes de usar Quizzy.",
    });
  }

  const method = (init.method ?? "GET").toUpperCase();
  const headers: Record<string, string> = {
    "X-Workspace-Id": workspaceId,
    ...(init.headers as Record<string, string> | undefined),
  };

  if (method !== "GET" && method !== "HEAD") {
    const csrf = await ensureCsrfToken(origin);
    if (csrf) headers["X-CSRFToken"] = csrf;
  }

  let body = init.body;
  if (init.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(init.json);
  }

  return fetch(`${origin}${path}`, {
    ...init,
    method,
    credentials: "include",
    headers,
    body,
  });
}

async function parseJsonOrThrow(response: Response): Promise<unknown> {
  if (response.status === 204) return null;
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(body ?? { detail: extractErrorMessage(body) });
  }
  return body;
}

export async function postQuizzyChat(input: {
  message: string;
  conversationId?: string | null;
}): Promise<QuizzyChatResponse> {
  const response = await quizzyFetch("/api/quizzy/chat/", {
    method: "POST",
    json: {
      message: input.message,
      conversation_id: input.conversationId ?? null,
    },
  });
  return (await parseJsonOrThrow(response)) as QuizzyChatResponse;
}

export async function listQuizzyConversations(): Promise<
  QuizzyConversationSummary[]
> {
  const response = await quizzyFetch("/api/quizzy/conversations/");
  return (await parseJsonOrThrow(response)) as QuizzyConversationSummary[];
}

export async function getQuizzyConversation(
  id: string,
): Promise<QuizzyConversationDetail> {
  const response = await quizzyFetch(`/api/quizzy/conversations/${id}/`);
  return (await parseJsonOrThrow(response)) as QuizzyConversationDetail;
}

export async function deleteQuizzyConversation(id: string): Promise<void> {
  const response = await quizzyFetch(`/api/quizzy/conversations/${id}/`, {
    method: "DELETE",
  });
  await parseJsonOrThrow(response);
}

export async function renameQuizzyConversation(
  id: string,
  title: string,
): Promise<QuizzyConversationSummary> {
  const response = await quizzyFetch(`/api/quizzy/conversations/${id}/`, {
    method: "PATCH",
    json: { title },
  });
  return (await parseJsonOrThrow(response)) as QuizzyConversationSummary;
}
