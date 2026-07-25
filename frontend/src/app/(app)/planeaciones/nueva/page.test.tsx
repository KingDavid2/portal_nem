import { act } from "react";
import { createRoot } from "react-dom/client";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  searchParamsGet: vi.fn<(key: string) => string | null>(),
  push: vi.fn<(url: string) => void>(),
  groupsQuery: { isLoading: false, isError: false, data: undefined as unknown },
  fieldsQuery: { isLoading: false, isError: false, data: undefined as unknown },
  catalogQuery: { isLoading: false, isError: false, data: undefined as unknown, _callArgs: undefined as unknown[] | undefined },
  quotaQuery: { isLoading: false, isError: false, data: undefined as unknown },
  mutate: vi.fn<(input: unknown, opts?: { onSuccess?: (plan: unknown) => void }) => void>(),
  createMutation: { isPending: false, error: undefined as unknown },
}));

vi.mock("next/navigation", () => ({
  useSearchParams: () => ({ get: mocks.searchParamsGet }),
  useRouter: () => ({ push: mocks.push }),
}));

vi.mock("@/lib/api/groups", () => ({ useGroupsQuery: () => mocks.groupsQuery }));
vi.mock("@/lib/api/lesson-plan-catalog", () => ({
  useLessonPlanFieldsQuery: () => mocks.fieldsQuery,
  useGenerationQuotaQuery: () => mocks.quotaQuery,
  useLessonPlanCatalogQuery: (...args: unknown[]) => {
    mocks.catalogQuery._callArgs = args;
    return mocks.catalogQuery;
  },
}));

vi.mock("@/lib/api/lesson-plans", () => ({
  useCreateLessonPlanMutation: () => ({ ...mocks.createMutation, mutate: mocks.mutate }),
}));

import Page from "./page";
import { ApiError } from "@/lib/api/errors";

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

/** Sets a controlled field's value the way React sees it. Assigning `.value`
 * directly is swallowed: React caches the last value on the node and treats an
 * event whose value it already knows as a no-op, so `onChange` never fires. */
function typeInto(el: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement, value: string) {
  const proto =
    el instanceof HTMLTextAreaElement
      ? window.HTMLTextAreaElement.prototype
      : el instanceof HTMLSelectElement
        ? window.HTMLSelectElement.prototype
        : window.HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(proto, "value")!.set!.call(el, value);
  el.dispatchEvent(new Event(el instanceof HTMLSelectElement ? "change" : "input", { bubbles: true }));
}

const click = (el: Element) => el.dispatchEvent(new MouseEvent("click", { bubbles: true }));

const buttonWith = (host: HTMLElement, text: string) =>
  [...host.querySelectorAll("button")].find((b) => b.textContent?.includes(text))!;

/** Fills every field `validateNewPlanForm` requires, through the real UI, so
 * "the CTA became clickable" means the actual form is submittable rather than
 * that a stub said so. */
async function completeTheForm(host: HTMLElement) {
  await act(async () => {
    typeInto(host.querySelector<HTMLSelectElement>("select[name='fieldId']")!, "languages");
  });
  await act(async () => {
    typeInto(host.querySelector<HTMLInputElement>("input[name='theme']")!, "El agua de la comunidad");
  });
  await act(async () => {
    typeInto(
      host.querySelector<HTMLTextAreaElement>("textarea[name='contextDiagnosis']")!,
      "Grupo con lectura irregular.",
    );
  });
  await act(async () => {
    typeInto(host.querySelector<HTMLInputElement>("input[name='startDate']")!, "2026-08-03");
  });

  // One eje.
  await act(async () => {
    click([...host.querySelectorAll("button[aria-pressed]")].find((c) => c.textContent === "Inclusión")!);
  });

  // One contenido with one PDA, through the picker.
  await act(async () => { click(buttonWith(host, "Elegir contenidos y PDAs")); });
  await act(async () => {
    click(
      [...host.querySelectorAll<HTMLInputElement>('input[type="checkbox"]')].find(
        (box) => box.getAttribute("aria-label") === "Seleccionar PDA",
      )!,
    );
  });
  await act(async () => { click(buttonWith(host, "Usar estos contenidos")); });
}

/** `mockCatalog` with the themes and contents the form needs to validate. */
const mockFullCatalog = {
  ...mockCatalog,
  cross_cutting_themes: [{ id: "inclusion", name: "Inclusión" }],
  contents: [
    {
      id: "c1",
      text: "Comprensión de textos literarios",
      pdas: [{ id: "p1", text: "Identifica el tema central" }],
    },
  ],
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
    mocks.quotaQuery = { isLoading: false, isError: false, data: undefined };
    mocks.createMutation = { isPending: false, error: undefined };
    mocks.push.mockReset();
    mocks.mutate.mockReset();
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

  it("the CTA stays disabled until the form is complete, then submits and redirects", async () => {
    const { host, root } = setupPage((k) => (k === "group" ? "10" : null));
    mocks.groupsQuery.data = mockGroups;
    mocks.fieldsQuery.data = mockFields;
    mocks.catalogQuery = { isLoading: false, isError: false, data: mockFullCatalog, _callArgs: undefined };
    await act(async () => { root.render(<Page />); });

    const cta = () => buttonWith(host, "Generar proyecto");
    expect(cta().disabled).toBe(true);
    expect(host.textContent).toContain("Falta por completar");

    await completeTheForm(host);
    expect(cta().disabled).toBe(false);
    expect(host.textContent).not.toContain("Falta por completar");

    await act(async () => { click(cta()); });
    expect(mocks.mutate).toHaveBeenCalledTimes(1);
    const [payload, opts] = mocks.mutate.mock.calls[0];
    expect(payload).toMatchObject({
      group: 10,
      field_id: "languages",
      methodology_id: "abp",
      theme: "El agua de la comunidad",
      cross_cutting_theme_ids: ["inclusion"],
      content_selections: [{ content_id: "c1", pda_ids: ["p1"] }],
    });

    await act(async () => { opts!.onSuccess!({ id: 77 }); });
    expect(mocks.push).toHaveBeenCalledWith("/planeaciones/77");
    await act(async () => { root.unmount(); });
  });

  it("a 429 surfaces the quota message rather than the generic error text", async () => {
    const { host, root } = setupPage((k) => (k === "group" ? "10" : null));
    mocks.groupsQuery.data = mockGroups;
    mocks.fieldsQuery.data = mockFields;
    mocks.catalogQuery = { isLoading: false, isError: false, data: mockFullCatalog, _callArgs: undefined };
    mocks.createMutation = {
      isPending: false,
      error: new ApiError({
        detail: "Monthly generation limit reached.",
        code: "generation_quota_exceeded",
        used: 2,
        limit: 2,
        period: "2026-07",
      }),
    };
    await act(async () => { root.render(<Page />); });

    expect(host.textContent).toContain(
      "Ya usaste tus 2 generaciones de este mes. El contador se reinicia el próximo mes.",
    );
    expect(host.textContent).not.toContain("Monthly generation limit reached.");
    await act(async () => { root.unmount(); });
  });

  it("any other create failure falls back to the API error message", async () => {
    const { host, root } = setupPage((k) => (k === "group" ? "10" : null));
    mocks.groupsQuery.data = mockGroups;
    mocks.fieldsQuery.data = mockFields;
    mocks.catalogQuery = { isLoading: false, isError: false, data: mockFullCatalog, _callArgs: undefined };
    mocks.createMutation = { isPending: false, error: new ApiError({ theme: ["Este campo es obligatorio."] }) };
    await act(async () => { root.render(<Page />); });

    expect(host.textContent).toContain("theme: Este campo es obligatorio.");
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