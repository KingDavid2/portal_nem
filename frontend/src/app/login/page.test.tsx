import { renderToStaticMarkup } from "react-dom/server";
import { act } from "react";
import { createRoot } from "react-dom/client";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ login: vi.fn(), push: vi.fn(), refresh: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mocks.push, refresh: mocks.refresh, replace: vi.fn() }) }));
vi.mock("@/lib/auth/auth-context", () => ({ useAuth: () => ({ login: mocks.login }) }));
vi.mock("@/lib/api/demo", async (importActual) => ({
  ...(await importActual<object>()),
  useDemoModeQuery: () => ({ data: false, isLoading: false, isError: false }),
}));
import LoginPage from "./page";

async function mount() {
  const host = document.createElement("div");
  const root = createRoot(host);
  await act(async () => root.render(<LoginPage />));
  return { host, root };
}

async function submit(host: HTMLDivElement, email: string, password: string) {
  const inputs = host.querySelectorAll("input");
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(inputs[0], email);
    inputs[0].dispatchEvent(new Event("input", { bubbles: true }));
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(inputs[1], password);
    inputs[1].dispatchEvent(new Event("input", { bubbles: true }));
  });
  await act(async () => host.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
}

describe("LoginPage", () => {
  beforeEach(() => { mocks.login.mockReset(); mocks.push.mockReset(); mocks.refresh.mockReset(); });

  it("renders the Spanish Pencil card with semantic shared primitives", () => {
    const html = renderToStaticMarkup(<LoginPage />);
    expect(html).toContain("portal NEM"); expect(html).toContain("Iniciar sesión"); expect(html).toContain("Correo electrónico"); expect(html).toContain("Contraseña"); expect(html).toContain("Entrar"); expect(html).toContain("max-w-[460px]");
  });

  it("submits credentials and redirects after login succeeds", async () => {
    mocks.login.mockResolvedValue(undefined);
    const { host, root } = await mount();
    await submit(host, "ana@example.com", "secret");
    expect(mocks.login).toHaveBeenCalledWith("ana@example.com", "secret");
    expect(mocks.push).toHaveBeenCalledWith("/"); expect(mocks.refresh).toHaveBeenCalledOnce();
    await act(async () => root.unmount());
  });

  it("shows the existing error and does not redirect after login fails", async () => {
    mocks.login.mockRejectedValue(new Error("bad credentials"));
    const { host, root } = await mount();
    await submit(host, "ana@example.com", "wrong");
    expect(host.textContent).toContain("Correo o contraseña incorrectos.");
    expect(mocks.push).not.toHaveBeenCalled(); expect(mocks.refresh).not.toHaveBeenCalled();
    await act(async () => root.unmount());
  });
});
