import { act } from "react";
import { createRoot } from "react-dom/client";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  searchParamsGet: vi.fn<(key: string) => string | null>(),
  push: vi.fn<(url: string) => void>(),
  groupsQuery: { isLoading: false, isError: false, data: undefined as unknown },
  fieldsQuery: { isLoading: false, isError: false, data: undefined as unknown },
  catalogQuery: { isLoading: false, isError: false, data: undefined as unknown, _callArgs: undefined as unknown[] | undefined },
}));

vi.mock("next/navigation", () => ({
  useSearchParams: () => ({ get: mocks.searchParamsGet }),
  useRouter: () => ({ push: mocks.push }),
}));

vi.mock("@/lib/api/groups", () => ({ useGroupsQuery: () => mocks.groupsQuery }));
vi.mock("@/lib/api/lesson-plan-catalog", () => ({
  useLessonPlanFieldsQuery: () => mocks.fieldsQuery,
  useLessonPlanCatalogQuery: (...args: unknown[]) => {
    mocks.catalogQuery._callArgs = args;
    return mocks.catalogQuery;
  },
}));

import Page from "./page";

const mockGroups = [
  { id: 10, school_year: 1, grado: 3, grupo: "A", workspace: "w1" },
  { id: 11, school_year: 1, grado: 3, grupo: "B", workspace: "w1" },
  { id: 12, school_year: 1, grado: 2, grupo: "C", workspace: "w1" },
];

const mockFields = [
  { id: "languages", name: "Lenguajes" },
  { id: "ethics-nature-society", name: "Ética, Naturaleza y Sociedades" },
];

const mockCatalog = {
  phase: 6,
  grade: 3,
  field: { id: "languages", name: "Lenguajes" },
  methodology: { id: "abp", name: "ABP Comunitario" },
  subjects: [{ id: "biologia", name: "Biología", field_id: "languages" }],
  cross_cutting_themes: [],
  contents: [],
  group: {
    id: 10,
    label: "3 A",
    grade: 3,
    school_name: "Esc. Sec. Gral. Jesús Reyes Heroles",
    school_cct: "13DES0042L",
    school_year_label: "2025–2026",
  },
  teacher: { email: "prof@correo.mx" },
};

function setupPage(searchParamsGet: (key: string) => string | null) {
  mocks.searchParamsGet.mockImplementation(searchParamsGet);
  const host = document.createElement("div");
  const root = createRoot(host);
  return { host, root };
}

describe("Nueva planeación", () => {
  beforeEach(() => {
    mocks.searchParamsGet.mockReturnValue(null);
    mocks.groupsQuery = { isLoading: false, isError: false, data: undefined };
    mocks.fieldsQuery = { isLoading: false, isError: false, data: undefined };
    mocks.catalogQuery = { isLoading: false, isError: false, data: undefined, _callArgs: undefined };
    mocks.push.mockReset();
  });

  it("renders the design strings", async () => {
    const { host, root } = setupPage(() => null);
    mocks.groupsQuery.data = mockGroups;
    mocks.fieldsQuery.data = mockFields;
    await act(async () => { root.render(<Page />); });
    expect(host.textContent).toContain("Nueva planeación");
    expect(host.textContent).toContain(
      "Tú defines el contexto y los PDAs. La IA solo secuencia los momentos.",
    );
    expect(host.textContent).toContain("Contexto del proyecto");
    expect(host.textContent).toContain("Escenario");
    await act(async () => { root.unmount(); });
  });

  it("prefills the Grupo select with ?group=12", async () => {
    const { host, root } = setupPage((k) => (k === "group" ? "12" : null));
    mocks.groupsQuery.data = mockGroups;
    mocks.fieldsQuery.data = mockFields;
    await act(async () => { root.render(<Page />); });
    expect(host.querySelector<HTMLSelectElement>("select[name='groupId']")!.value).toBe("12");
    await act(async () => { root.unmount(); });
  });

  it("catalog query is not enabled when no group", async () => {
    mocks.catalogQuery = { isLoading: true, isError: false, data: undefined, _callArgs: undefined };
    const { root } = setupPage(() => null);
    await act(async () => { root.render(<Page />); });
    const args = mocks.catalogQuery._callArgs;
    expect(args?.[0]).toBeNull();
    expect(args?.[1]).toBe("");
    expect(mocks.catalogQuery.isLoading).toBe(true);
    await act(async () => { root.unmount(); });
  });

  it("renders the automatic data banner when catalog has data", async () => {
    const { host, root } = setupPage((k) => (k === "group" ? "10" : null));
    mocks.groupsQuery.data = mockGroups;
    mocks.fieldsQuery.data = mockFields;
    mocks.catalogQuery = { isLoading: false, isError: false, data: mockCatalog, _callArgs: undefined };
    await act(async () => { root.render(<Page />); });
    expect(host.textContent).toContain("Esc. Sec. Gral. Jesús Reyes Heroles");
    expect(host.textContent).toContain("13DES0042L");
    expect(host.textContent).toContain("2025–2026");
    expect(host.textContent).toContain("prof@correo.mx");

    // CCT is optional upstream: a blank one falls back to an em dash rather
    // than collapsing the pair to a stray label.
    mocks.catalogQuery = {
      isLoading: false,
      isError: false,
      data: { ...mockCatalog, group: { ...mockCatalog.group, school_cct: "" } },
      _callArgs: undefined,
    };
    await act(async () => { root.render(<Page />); });
    expect(host.textContent).not.toContain("13DES0042L");
    expect(host.textContent).toContain("CCT—");
    await act(async () => { root.unmount(); });
  });

  it("scenario chip: clicking Comunidad leaves it at community, clicking Aula switches", async () => {
    const { host, root } = setupPage((k) => (k === "group" ? "10" : null));
    mocks.groupsQuery.data = mockGroups;
    mocks.fieldsQuery.data = mockFields;
    mocks.catalogQuery = { isLoading: false, isError: false, data: mockCatalog, _callArgs: undefined };
    await act(async () => { root.render(<Page />); });
    const chips = host.querySelectorAll("button[aria-pressed]");
    const comunidadChip = [...chips].find((c) => c.textContent?.includes("Comunidad"));
    const aulaChip = [...chips].find((c) => c.textContent?.includes("Aula"));

    expect((comunidadChip as HTMLElement).ariaPressed).toBe("true");

    await act(async () => {
      aulaChip!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
    expect((aulaChip as HTMLElement).ariaPressed).toBe("true");
    expect((comunidadChip as HTMLElement).ariaPressed).toBe("false");

    await act(async () => {
      comunidadChip!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
    expect((comunidadChip as HTMLElement).ariaPressed).toBe("true");
    expect((aulaChip as HTMLElement).ariaPressed).toBe("false");
    await act(async () => { root.unmount(); });
  });
});