import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const auth = vi.hoisted(() => ({ value: { user: null as { id: string } | null, isLoading: false } }));
const workspace = vi.hoisted(() => ({ value: null as string | null }));
const pathname = vi.hoisted(() => ({ value: "/schools" }));

vi.mock("@/lib/auth/auth-context", () => ({ useAuth: () => auth.value }));
vi.mock("@/lib/workspace/use-active-workspace", () => ({ useActiveWorkspaceId: () => [workspace.value, vi.fn()] }));
vi.mock("next/navigation", () => ({ usePathname: () => pathname.value }));
vi.mock("@/components/workspace-switcher", () => ({ WorkspaceSwitcher: () => <div>Workspace switcher</div> }));
vi.mock("@/components/logout-button", () => ({ LogoutButton: () => <button>Log out</button> }));

import AppLayout from "./layout";

const render = () => renderToStaticMarkup(<AppLayout><p>Screen content</p></AppLayout>);

describe("AppLayout gates", () => {
  beforeEach(() => { auth.value = { user: null, isLoading: false }; workspace.value = null; pathname.value = "/schools"; });

  it("shows only the loading gate while the session resolves", () => {
    auth.value = { user: null, isLoading: true };
    const html = render();
    expect(html).toContain("Cargando sesión…");
    expect(html).not.toContain("Screen content");
  });

  it("sends unauthenticated users to login before the shell", () => {
    const html = render();
    expect(html).toContain("Debes iniciar sesión primero.");
    expect(html).toContain('href="/login"');
    expect(html).not.toContain("Workspace switcher");
  });

  it("requires a workspace before the shell", () => {
    auth.value = { user: { id: "u1" }, isLoading: false };
    const html = render();
    expect(html).toContain("Selecciona un workspace");
    expect(html).toContain('href="/"');
    expect(html).not.toContain("Workspace switcher");
  });

  it("renders the sidebar shell only with user and workspace", () => {
    auth.value = { user: { id: "u1" }, isLoading: false };
    workspace.value = "w1";
    const html = render();
    expect(html).toContain("Workspace switcher");
    expect(html).toContain("Screen content");
    expect(html).toContain('aria-label="Navegación principal"');
  });
});
