import createClient, { type Middleware } from "openapi-fetch";
import type { paths } from "./schema";
import { getActiveWorkspaceId } from "@/lib/workspace/store";

/**
 * Session/CSRF/workspace fetch layer (frontend-foundation spec — "Session/CSRF
 * Auth Lifecycle", "Active-Workspace Context on Every Data Request";
 * design.md "Frontend fetch layer").
 *
 * - `credentials: "include"` on every request (set on the client below).
 * - Unsafe methods (POST/PUT/PATCH/DELETE) get an `X-CSRFToken` header,
 *   echoing the `csrftoken` cookie; the cookie is bootstrapped via
 *   `GET /api/auth/csrf/` first if missing.
 * - Every "data" request (i.e. not `/api/auth/*` and not the unscoped
 *   `/api/workspaces/` list) gets `X-Workspace-Id` from the active-workspace
 *   store. If no workspace is selected yet, the request is refused
 *   client-side rather than sent without the header.
 */

const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export function isAuthPath(pathname: string): boolean {
  return pathname.startsWith("/api/auth/");
}

export function isWorkspaceListPath(pathname: string): boolean {
  return pathname === "/api/workspaces/" || pathname === "/api/workspaces";
}

/** Guest paths do not require an active workspace or authentication —
 * demo endpoints and the health probe must be reachable by unauthenticated
 * visitors before they have a workspace selected. */
export function isGuestPath(pathname: string): boolean {
  return pathname.startsWith("/api/demo/") || pathname === "/api/health/";
}

/** A "data" request is any request that must carry the active workspace's
 * `X-Workspace-Id` — everything except the auth surface, the unscoped
 * workspace-list endpoint, and guest paths (design.md: workspace-list "must
 * not require `X-Workspace-Id`"). */
export function isDataRequest(pathname: string): boolean {
  return !isAuthPath(pathname) && !isWorkspaceListPath(pathname) && !isGuestPath(pathname);
}

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

/** Thrown by the fetch middleware when a data request would otherwise be
 * sent with no active workspace selected. Callers (screens, hooks) should
 * treat this as "select a workspace first", not a network failure. */
export class MissingWorkspaceError extends Error {
  constructor() {
    super("No active workspace selected; refusing to send data request.");
    this.name = "MissingWorkspaceError";
  }
}

export const authMiddleware: Middleware = {
  async onRequest({ request }) {
    const url = new URL(request.url);

    if (UNSAFE_METHODS.has(request.method)) {
      const csrfToken = await ensureCsrfToken(url.origin);
      if (csrfToken) {
        request.headers.set("X-CSRFToken", csrfToken);
      }
    }

    if (isDataRequest(url.pathname)) {
      const workspaceId = getActiveWorkspaceId();
      if (!workspaceId) {
        throw new MissingWorkspaceError();
      }
      request.headers.set("X-Workspace-Id", workspaceId);
    }

    return request;
  },
};

const client = createClient<paths>({
  baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  credentials: "include",
});

client.use(authMiddleware);

export default client;
