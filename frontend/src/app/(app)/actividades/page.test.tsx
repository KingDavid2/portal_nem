import { act } from "react";
import { createRoot } from "react-dom/client";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ActivitiesListResponse, Activity, ActivityCreate } from "@/lib/api/grades";

const mocks = vi.hoisted(() => ({
  groupId: 10 as number | null,
  setGroupId: vi.fn<(id: number | null) => void>(),
  visibleGroups: [{ id: 10, grado: 3, grupo: "A", school_year: 1, workspace: "w1" }],
  activitiesQuery: {
    isLoading: false,
    isError: false,
    isSuccess: true,
    data: undefined as ActivitiesListResponse | undefined,
    isFetching: false,
  },
  createMutate: vi.fn<
    (input: ActivityCreate, opts?: { onSuccess?: (a: Activity) => void }) => void
  >(),
  createMutation: { isPending: false, error: undefined as unknown },
  fieldsQuery: { isLoading: false, isError: false, data: [{ id: "languages", name: "Lenguajes" }] },
  catalogQuery: {
    isLoading: false,
    isError: false,
    data: { subjects: [{ id: "espanol", name: "Español", field_id: "languages" }] },
  },
}));

vi.mock("@/lib/school-context/school-teaching-context", () => ({
  useSchoolTeachingContext: () => ({
    groupId: mocks.groupId,
    setGroupId: mocks.setGroupId,
    visibleGroups: mocks.visibleGroups,
    schools: [],
    schoolYears: [],
    groups: [],
    visibleSchoolYears: [],
    isReady: true,
    schoolId: 1,
    schoolYearId: 2,
    setSchoolId: vi.fn(),
    setSchoolYearId: vi.fn(),
  }),
}));

vi.mock("@/lib/api/grades", () => ({
  useActivitiesQuery: () => mocks.activitiesQuery,
  useCreateActivityMutation: () => ({ ...mocks.createMutation, mutate: mocks.createMutate }),
  useScoreMatrixQuery: () => ({ isLoading: false, isError: false, isSuccess: false, data: undefined }),
  useBulkUpsertScoresMutation: () => ({ isPending: false, mutate: vi.fn() }),
}));

vi.mock("@/lib/api/lesson-plan-catalog", () => ({
  useLessonPlanFieldsQuery: () => mocks.fieldsQuery,
  useLessonPlanCatalogQuery: () => mocks.catalogQuery,
}));

import Page from "./page";

const listResponse: ActivitiesListResponse = {
  terms: [
    { id: 1, number: 1 },
    { id: 2, number: 2 },
    { id: 3, number: 3 },
  ],
  activities: [
    {
      id: 101,
      group: 10,
      term: 1,
      title: "Ensayo del agua",
      type: "task",
      due_date: "2026-08-15",
      field: "languages",
      subject_ids: ["espanol"],
      description: "",
    },
  ],
  stats: {
    total_activities: 1,
    graded_activities: 0,
    pending_activities: 1,
    average_score: null,
  },
};

const click = (el: Element) => el.dispatchEvent(new MouseEvent("click", { bubbles: true }));

function typeInto(el: HTMLInputElement | HTMLSelectElement, value: string) {
  const proto =
    el instanceof HTMLSelectElement
      ? window.HTMLSelectElement.prototype
      : window.HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(proto, "value")!.set!.call(el, value);
  el.dispatchEvent(new Event(el instanceof HTMLSelectElement ? "change" : "input", { bubbles: true }));
}

const btn = (host: HTMLElement, text: string) =>
  [...host.querySelectorAll("button")].find((b) => b.textContent?.includes(text))!;

async function mount() {
  const host = document.createElement("div");
  const root = createRoot(host);
  await act(async () => {
    root.render(<Page />);
  });
  return { host, root };
}

async function withPeriodo(host: HTMLElement) {
  await act(async () => {
    typeInto(host.querySelector<HTMLSelectElement>("select[name='termId']")!, "1");
  });
}

describe("/actividades — Por actividad (D3)", () => {
  beforeEach(() => {
    mocks.groupId = 10;
    mocks.activitiesQuery = {
      isLoading: false,
      isError: false,
      isSuccess: true,
      data: listResponse,
      isFetching: false,
    };
    mocks.createMutate.mockReset();
    mocks.createMutation = { isPending: false, error: undefined };
  });

  it("requires Periodo before listing — empty Periodo hides activities", async () => {
    const { host, root } = await mount();
    expect(host.textContent).toMatch(/Periodo/i);
    expect(host.textContent).not.toContain("Ensayo del agua");
    expect(host.textContent).toMatch(/selecciona un periodo/i);
    await act(async () => root.unmount());
  });

  it("loads Por actividad list when Periodo is selected", async () => {
    const { host, root } = await mount();
    await withPeriodo(host);
    expect(host.textContent).toContain("Ensayo del agua");
    expect(host.textContent).toMatch(/Por actividad/);
    await act(async () => root.unmount());
  });

  it("Nueva actividad opens a local role=dialog", async () => {
    const { host, root } = await mount();
    await withPeriodo(host);
    expect(host.querySelector('[role="dialog"]')).toBeNull();
    await act(async () => {
      click(btn(host, "Nueva actividad"));
    });
    const dialog = host.querySelector('[role="dialog"]');
    expect(dialog).not.toBeNull();
    expect(dialog?.getAttribute("aria-modal")).toBe("true");
    await act(async () => root.unmount());
  });

  it("modal submit calls POST create (immediate persist)", async () => {
    const { host, root } = await mount();
    await withPeriodo(host);
    await act(async () => {
      click(btn(host, "Nueva actividad"));
    });
    const d = host.querySelector<HTMLElement>('[role="dialog"]')!;
    await act(async () => {
      typeInto(d.querySelector<HTMLInputElement>("input[name='title']")!, "Proyecto comunidad");
      typeInto(d.querySelector<HTMLSelectElement>("select[name='type']")!, "project");
      typeInto(d.querySelector<HTMLInputElement>("input[name='due_date']")!, "2026-09-01");
      typeInto(d.querySelector<HTMLSelectElement>("select[name='field']")!, "languages");
    });
    await act(async () => {
      click(d.querySelector<HTMLInputElement>('input[type="checkbox"][value="espanol"]')!);
    });
    await act(async () => {
      click(btn(d, "Crear actividad"));
    });
    expect(mocks.createMutate).toHaveBeenCalledTimes(1);
    expect(mocks.createMutate.mock.calls[0]![0]).toMatchObject({
      group: 10,
      term: 1,
      title: "Proyecto comunidad",
      type: "project",
      due_date: "2026-09-01",
      field: "languages",
      subject_ids: ["espanol"],
    });
    await act(async () => root.unmount());
  });

  it("Por actividad has no score Guardar and no Exportar", async () => {
    const { host, root } = await mount();
    await withPeriodo(host);
    const labels = [...host.querySelectorAll("button")].map((b) => b.textContent?.trim() ?? "");
    expect(labels.some((t) => /^Guardar$/i.test(t) || /^Guardar calificaciones$/i.test(t))).toBe(false);
    expect(host.textContent).not.toMatch(/Exportar/i);
    await act(async () => root.unmount());
  });
});
