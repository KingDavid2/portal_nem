import { act } from "react";
import { createRoot } from "react-dom/client";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  sessionQuery: {
    data: undefined as unknown,
    isLoading: true,
    isError: false,
  },
  mutate: vi.fn(),
  push: vi.fn(),
  setActiveWorkspaceId: vi.fn(),
  refetchQueries: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mocks.push }),
}));

vi.mock("@/lib/api/demo", async (importActual) => ({
  ...(await importActual<object>()),
  useDemoSessionQuery: () => mocks.sessionQuery,
}));

vi.mock("@/lib/workspace/store", async (importActual) => ({
  ...(await importActual<object>()),
  setActiveWorkspaceId: mocks.setActiveWorkspaceId,
}));

vi.mock("@tanstack/react-query", async (importActual) => ({
  ...(await importActual<object>()),
  useQueryClient: () => ({ refetchQueries: mocks.refetchQueries }),
}));

import DemoSessionPage from "./page";

async function mount(id = "abc") {
  const host = document.createElement("div");
  const root = createRoot(host);
  await act(async () =>
    root.render(<DemoSessionPage params={Promise.resolve({ id })} />),
  );
  return { host, root };
}

describe("DemoSessionPage", () => {
  beforeEach(() => {
    mocks.sessionQuery = {
      data: undefined,
      isLoading: true,
      isError: false,
    };
    mocks.push.mockReset();
    mocks.setActiveWorkspaceId.mockReset();
    mocks.refetchQueries.mockReset();
    mocks.refetchQueries.mockResolvedValue(undefined);
  });

  it("shows preparing message while session is pending", async () => {
    mocks.sessionQuery = {
      data: {
        id: "abc",
        persona: "teacher_minimal",
        status: "pending",
        workspace: null,
        email: null,
        error_message: "",
      },
      isLoading: false,
      isError: false,
    };
    const { host, root } = await mount();
    expect(host.textContent).toContain("Preparando tu espacio de trabajo");
    await act(async () => root.unmount());
  });

  it("shows preparing message while session is loading", async () => {
    mocks.sessionQuery = {
      data: undefined,
      isLoading: true,
      isError: false,
    };
    const { host, root } = await mount();
    expect(host.textContent).toContain("Preparando tu espacio de trabajo");
    await act(async () => root.unmount());
  });

  it("on ready: sets workspace, refetches auth, and redirects to /", async () => {
    mocks.sessionQuery = {
      data: {
        id: "abc",
        persona: "teacher_full",
        status: "ready",
        workspace: "ws-1",
        email: "demo@example.com",
        error_message: "",
      },
      isLoading: false,
      isError: false,
    };
    const { root } = await mount();

    expect(mocks.setActiveWorkspaceId).toHaveBeenCalledWith("ws-1");
    expect(mocks.refetchQueries).toHaveBeenCalledWith({
      queryKey: ["auth", "me"],
    });
    expect(mocks.push).toHaveBeenCalledWith("/");
    await act(async () => root.unmount());
  });

  // The bounce-back guard: `useMeQuery` holds a cached `null` from when this
  // guest was logged out. If `/` mounts before the auth refetch lands,
  // `useDemoGuestRedirect` reads that stale `null` and sends the freshly
  // signed-in user straight back to the persona picker.
  it("on ready: does not redirect until the auth refetch has resolved", async () => {
    let resolveRefetch: () => void = () => {};
    mocks.refetchQueries.mockReturnValue(
      new Promise<void>((resolve) => {
        resolveRefetch = resolve;
      }),
    );
    mocks.sessionQuery = {
      data: {
        id: "abc",
        persona: "teacher_full",
        status: "ready",
        workspace: "ws-1",
        email: "demo@example.com",
        error_message: "",
      },
      isLoading: false,
      isError: false,
    };
    const { root } = await mount();

    expect(mocks.refetchQueries).toHaveBeenCalled();
    expect(mocks.push).not.toHaveBeenCalled();

    await act(async () => {
      resolveRefetch();
    });

    expect(mocks.push).toHaveBeenCalledWith("/");
    await act(async () => root.unmount());
  });

  it("on ready: enters only once even when the session object re-renders", async () => {
    const session = {
      id: "abc",
      persona: "teacher_full",
      status: "ready",
      workspace: "ws-1",
      email: "demo@example.com",
      error_message: "",
    };
    mocks.sessionQuery = { data: session, isLoading: false, isError: false };
    const host = document.createElement("div");
    const root = createRoot(host);
    await act(async () =>
      root.render(<DemoSessionPage params={Promise.resolve({ id: "abc" })} />),
    );

    // A poll tick hands back an equal-but-not-identical object; the effect
    // re-runs and must not fire a second navigation.
    mocks.sessionQuery = {
      data: { ...session },
      isLoading: false,
      isError: false,
    };
    await act(async () =>
      root.render(<DemoSessionPage params={Promise.resolve({ id: "abc" })} />),
    );

    expect(mocks.push).toHaveBeenCalledTimes(1);
    await act(async () => root.unmount());
  });

  it("on ready with null workspace: does not call setActiveWorkspaceId", async () => {
    mocks.sessionQuery = {
      data: {
        id: "abc",
        persona: "teacher_full",
        status: "ready",
        workspace: null,
        email: "demo@example.com",
        error_message: "",
      },
      isLoading: false,
      isError: false,
    };
    const { root } = await mount();

    expect(mocks.setActiveWorkspaceId).not.toHaveBeenCalled();
    await act(async () => root.unmount());
  });

  it("on failed: renders error_message and back link", async () => {
    mocks.sessionQuery = {
      data: {
        id: "abc",
        persona: "teacher_full",
        status: "failed",
        workspace: null,
        email: null,
        error_message: "El servidor de demostración está ocupado.",
      },
      isLoading: false,
      isError: false,
    };
    const { host, root } = await mount();
    expect(host.textContent).toContain("El servidor de demostración está ocupado.");
    expect(host.textContent).toContain("Volver a elegir perfil");
    const alert = host.querySelector('[role="alert"]');
    expect(alert).not.toBeNull();
    await act(async () => root.unmount());
  });

  it("on failed with empty error_message: renders generic error", async () => {
    mocks.sessionQuery = {
      data: {
        id: "abc",
        persona: "teacher_full",
        status: "failed",
        workspace: null,
        email: null,
        error_message: "",
      },
      isLoading: false,
      isError: false,
    };
    const { host, root } = await mount();
    expect(host.textContent).toContain("No se pudo preparar tu espacio de demostración");
    expect(host.textContent).toContain("Volver a elegir perfil");
    await act(async () => root.unmount());
  });

  it("on query error: renders alert and back link", async () => {
    mocks.sessionQuery = {
      data: undefined,
      isLoading: false,
      isError: true,
    };
    const { host, root } = await mount();
    const alert = host.querySelector('[role="alert"]');
    expect(alert).not.toBeNull();
    expect(host.textContent).toContain("Volver a elegir perfil");
    await act(async () => root.unmount());
  });
});
