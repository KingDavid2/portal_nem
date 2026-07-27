import { act } from "react";
import { createRoot } from "react-dom/client";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  demoModeQuery: {
    data: undefined as unknown,
    isLoading: true,
    isError: false,
  },
  auth: {
    user: null as unknown,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
  },
  replace: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mocks.replace }),
}));

vi.mock("@/lib/api/demo", async (importActual) => ({
  ...(await importActual<object>()),
  useDemoModeQuery: () => mocks.demoModeQuery,
}));

vi.mock("@/lib/auth/auth-context", () => ({
  useAuth: () => mocks.auth,
}));

import { useDemoGuestRedirect } from "./use-demo-guest-redirect";

function TestComponent() {
  useDemoGuestRedirect();
  return <div>test</div>;
}

async function mount() {
  const host = document.createElement("div");
  const root = createRoot(host);
  await act(async () => root.render(<TestComponent />));
  return { host, root };
}

describe("useDemoGuestRedirect", () => {
  beforeEach(() => {
    mocks.demoModeQuery = { data: undefined, isLoading: true, isError: false };
    mocks.auth = { user: null, isLoading: false, login: vi.fn(), logout: vi.fn() };
    mocks.replace.mockReset();
  });

  it("redirects to /demo when demo mode is on and no user", async () => {
    mocks.demoModeQuery = { data: true, isLoading: false, isError: false };
    mocks.auth = { user: null, isLoading: false, login: vi.fn(), logout: vi.fn() };
    const { root } = await mount();
    expect(mocks.replace).toHaveBeenCalledWith("/demo");
    await act(async () => root.unmount());
  });

  it("does not redirect when demo mode is on but user is present", async () => {
    mocks.demoModeQuery = { data: true, isLoading: false, isError: false };
    mocks.auth = { user: { id: 1, email: "test@example.com" }, isLoading: false, login: vi.fn(), logout: vi.fn() };
    const { root } = await mount();
    expect(mocks.replace).not.toHaveBeenCalled();
    await act(async () => root.unmount());
  });

  it("does not redirect when demo mode is on but auth is still loading", async () => {
    mocks.demoModeQuery = { data: true, isLoading: false, isError: false };
    mocks.auth = { user: null, isLoading: true, login: vi.fn(), logout: vi.fn() };
    const { root } = await mount();
    expect(mocks.replace).not.toHaveBeenCalled();
    await act(async () => root.unmount());
  });

  it("does not redirect when demo mode is off", async () => {
    mocks.demoModeQuery = { data: false, isLoading: false, isError: false };
    mocks.auth = { user: null, isLoading: false, login: vi.fn(), logout: vi.fn() };
    const { root } = await mount();
    expect(mocks.replace).not.toHaveBeenCalled();
    await act(async () => root.unmount());
  });

  it("does not redirect when demo mode query is still loading", async () => {
    mocks.demoModeQuery = { data: undefined, isLoading: true, isError: false };
    mocks.auth = { user: null, isLoading: false, login: vi.fn(), logout: vi.fn() };
    const { root } = await mount();
    expect(mocks.replace).not.toHaveBeenCalled();
    await act(async () => root.unmount());
  });
});
