import { beforeEach, describe, expect, it, vi } from "vitest";

/**
 * Focused unit tests for the CSRF-echo / X-Workspace-Id fetch middleware
 * (frontend-foundation spec — "Session/CSRF Auth Lifecycle", "Active-Workspace
 * Context on Every Data Request"; tasks.md D6.4 `npm test -- fetch-client`).
 *
 * The active-workspace store is mocked directly rather than exercised via
 * real `localStorage`: Node's built-in Storage global and jsdom's can
 * disagree across environments, and this test is about the fetch layer's own
 * contract (what it does with whatever `getActiveWorkspaceId()` returns), not
 * about the storage backend covered separately in `lib/workspace/store.ts`.
 */

let activeWorkspaceId: string | null = null;

vi.mock("@/lib/workspace/store", () => ({
  getActiveWorkspaceId: () => activeWorkspaceId,
}));

const {
  authMiddleware,
  isAuthPath,
  isDataRequest,
  isGuestPath,
  isWorkspaceListPath,
  MissingWorkspaceError,
} = await import("./client");

function clearCsrfCookie() {
  document.cookie = "csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/";
}

function makeRequest(method: string, path: string): Request {
  return new Request(`http://localhost:8000${path}`, { method });
}

async function runOnRequest(request: Request): Promise<Request> {
  const result = await authMiddleware.onRequest!({
    request,
    schemaPath: "",
    params: {},
    id: "test",
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    options: {} as any,
  });
  return result as Request;
}

describe("path classification", () => {
  it("classifies /api/auth/* as the auth surface", () => {
    expect(isAuthPath("/api/auth/me/")).toBe(true);
    expect(isAuthPath("/api/schools/")).toBe(false);
  });

  it("classifies /api/workspaces/ as the unscoped workspace-list path", () => {
    expect(isWorkspaceListPath("/api/workspaces/")).toBe(true);
    expect(isWorkspaceListPath("/api/schools/")).toBe(false);
  });

  it("treats /api/demo/* and /api/health/ as guest paths", () => {
    expect(isGuestPath("/api/demo/personas/")).toBe(true);
    expect(isGuestPath("/api/demo/sessions/")).toBe(true);
    expect(isGuestPath("/api/demo/sessions/abc-123/")).toBe(true);
    expect(isGuestPath("/api/health/")).toBe(true);
    expect(isGuestPath("/api/schools/")).toBe(false);
    expect(isGuestPath("/api/auth/me/")).toBe(false);
  });

  it("treats everything except auth, workspace-list, and guest paths as a data request", () => {
    expect(isDataRequest("/api/schools/")).toBe(true);
    expect(isDataRequest("/api/auth/me/")).toBe(false);
    expect(isDataRequest("/api/workspaces/")).toBe(false);
    expect(isDataRequest("/api/demo/personas/")).toBe(false);
    expect(isDataRequest("/api/demo/sessions/abc/")).toBe(false);
    expect(isDataRequest("/api/health/")).toBe(false);
  });
});

describe("authMiddleware.onRequest", () => {
  beforeEach(() => {
    clearCsrfCookie();
    activeWorkspaceId = null;
    vi.restoreAllMocks();
  });

  it("attaches X-CSRFToken from an existing cookie on unsafe methods", async () => {
    document.cookie = "csrftoken=abc123";
    activeWorkspaceId = "workspace-1";

    const result = await runOnRequest(makeRequest("POST", "/api/schools/"));

    expect(result.headers.get("X-CSRFToken")).toBe("abc123");
  });

  it("bootstraps the CSRF cookie via GET /api/auth/csrf/ when the cookie is missing", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async () => {
        document.cookie = "csrftoken=bootstrapped";
        return new Response(null, { status: 200 });
      });
    activeWorkspaceId = "workspace-1";

    const result = await runOnRequest(makeRequest("POST", "/api/schools/"));

    expect(fetchSpy).toHaveBeenCalledWith(
      "http://localhost:8000/api/auth/csrf/",
      expect.objectContaining({ credentials: "include" }),
    );
    expect(result.headers.get("X-CSRFToken")).toBe("bootstrapped");
  });

  it("does not attach X-Workspace-Id on /api/auth/* or /api/workspaces/ requests", async () => {
    const authResult = await runOnRequest(makeRequest("GET", "/api/auth/me/"));
    expect(authResult.headers.get("X-Workspace-Id")).toBeNull();

    activeWorkspaceId = "workspace-1";
    const workspacesResult = await runOnRequest(
      makeRequest("GET", "/api/workspaces/"),
    );
    expect(workspacesResult.headers.get("X-Workspace-Id")).toBeNull();
  });

  it("does not throw or attach X-Workspace-Id on guest paths even without workspace", async () => {
    activeWorkspaceId = null;
    const demoResult = await runOnRequest(makeRequest("GET", "/api/demo/personas/"));
    expect(demoResult.headers.get("X-Workspace-Id")).toBeNull();

    const healthResult = await runOnRequest(makeRequest("GET", "/api/health/"));
    expect(healthResult.headers.get("X-Workspace-Id")).toBeNull();
  });

  it("attaches X-Workspace-Id on data requests when a workspace is active", async () => {
    activeWorkspaceId = "workspace-42";

    const result = await runOnRequest(makeRequest("GET", "/api/schools/"));

    expect(result.headers.get("X-Workspace-Id")).toBe("workspace-42");
  });

  it("refuses (throws) data requests when no workspace is selected", async () => {
    await expect(
      runOnRequest(makeRequest("GET", "/api/schools/")),
    ).rejects.toBeInstanceOf(MissingWorkspaceError);
  });
});
