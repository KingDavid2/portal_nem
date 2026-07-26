import { act } from "react";
import { createRoot } from "react-dom/client";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  personas: {
    isLoading: true,
    isError: false,
    data: undefined as unknown,
  },
  mutate: vi.fn(),
  push: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mocks.push }),
}));

vi.mock("@/lib/api/demo", async (importActual) => ({
  ...(await importActual<object>()),
  useDemoPersonasQuery: () => mocks.personas,
  useCreateDemoSessionMutation: () => ({
    mutate: mocks.mutate,
    isPending: false,
  }),
}));

import DemoPage from "./page";

async function mount() {
  const host = document.createElement("div");
  const root = createRoot(host);
  await act(async () => root.render(<DemoPage />));
  return { host, root };
}

describe("DemoPage", () => {
  beforeEach(() => {
    mocks.personas = { isLoading: true, isError: false, data: undefined };
    mocks.mutate.mockReset();
    mocks.push.mockReset();
  });

  it("shows loading state", async () => {
    mocks.personas = { isLoading: true, isError: false, data: undefined };
    const { host, root } = await mount();
    expect(host.textContent).toContain("Cargando perfiles de demostración");
    await act(async () => root.unmount());
  });

  it("shows error state when query fails", async () => {
    mocks.personas = { isLoading: false, isError: true, data: undefined };
    const { host, root } = await mount();
    expect(host.textContent).toContain("No se pudieron cargar los perfiles");
    await act(async () => root.unmount());
  });

  it("renders persona cards with labels, descriptions, and features", async () => {
    mocks.personas = {
      isLoading: false,
      isError: false,
      data: [
        {
          key: "teacher_minimal",
          label: "Docente básico",
          description: "Un perfil con datos mínimos.",
          features: ["Sin planeaciones", "Sin grupos activos"],
        },
      ],
    };
    const { host, root } = await mount();
    expect(host.textContent).toContain("Docente básico");
    expect(host.textContent).toContain("Un perfil con datos mínimos");
    expect(host.textContent).toContain("Sin planeaciones");
    expect(host.textContent).toContain("Sin grupos activos");
    expect(host.textContent).toContain("Probar");
    await act(async () => root.unmount());
  });

  it("shows the demo password in the footer", async () => {
    mocks.personas = {
      isLoading: false,
      isError: false,
      data: [
        { key: "teacher_minimal", label: "Docente", description: "Desc", features: [] },
      ],
    };
    const { host, root } = await mount();
    expect(host.textContent).toContain("DemoPlan2026!");
    await act(async () => root.unmount());
  });

  it("calls mutate with persona key and routes to demo session", async () => {
    mocks.personas = {
      isLoading: false,
      isError: false,
      data: [
        { key: "teacher_full", label: "Docente completo", description: "Full", features: [] },
      ],
    };
    const { host, root } = await mount();
    const button = host.querySelector("button")!;
    await act(async () => button.dispatchEvent(new MouseEvent("click", { bubbles: true })));
    const [personaKey, options] = mocks.mutate.mock.calls[0];
    expect(personaKey).toBe("teacher_full");
    await act(async () => {
      options?.onSuccess({
        id: "demo-session-abc",
        persona: "teacher_full",
        status: "pending",
        workspace: null,
        email: null,
        error_message: "",
      });
    });
    expect(mocks.push).toHaveBeenCalledWith("/demo/demo-session-abc");
    await act(async () => root.unmount());
  });
});