import { act } from "react";
import { createRoot } from "react-dom/client";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type {
  ActivitiesFilters,
  ActivitiesListResponse,
  Activity,
  ActivityCreate,
  ScoresBulkRequest,
  ScoresMatrixResponse,
  TypeEnum,
} from "@/lib/api/grades";

type ActivitiesArgs = [number | null, number | null, ActivitiesFilters?];
type MatrixArgs = [number | null, number | null, Omit<ActivitiesFilters, "q">?];

const mocks = vi.hoisted(() => ({
  groupId: 10 as number | null,
  setGroupId: vi.fn<(id: number | null) => void>(),
  visibleGroups: [{ id: 10, grado: 3, grupo: "A", school_year: 1, workspace: "w1" }],
  activitiesCalls: [] as ActivitiesArgs[],
  matrixCalls: [] as MatrixArgs[],
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
  matrixQuery: {
    isLoading: false,
    isError: false,
    isSuccess: true,
    data: undefined as ScoresMatrixResponse | undefined,
    isFetching: false,
  },
  bulkMutate: vi.fn<
    (input: ScoresBulkRequest, opts?: { onSuccess?: () => void }) => void
  >(),
  bulkMutation: { isPending: false, error: undefined as unknown },
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

vi.mock("@/lib/api/grades", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/grades")>();
  return {
    ...actual,
    useActivitiesQuery: (...args: ActivitiesArgs) => {
      mocks.activitiesCalls.push(args);
      return mocks.activitiesQuery;
    },
    useCreateActivityMutation: () => ({ ...mocks.createMutation, mutate: mocks.createMutate }),
    useScoreMatrixQuery: (...args: MatrixArgs) => {
      mocks.matrixCalls.push(args);
      return mocks.matrixQuery;
    },
    useBulkUpsertScoresMutation: () => ({ ...mocks.bulkMutation, mutate: mocks.bulkMutate }),
  };
});

vi.mock("@/lib/api/lesson-plan-catalog", () => ({
  useLessonPlanFieldsQuery: () => mocks.fieldsQuery,
  useLessonPlanCatalogQuery: () => mocks.catalogQuery,
}));

import Page, { displayAverage, displayScore, scoreDraftKey } from "./page";
import { activitiesQueryEnabled } from "@/lib/api/grades";

const activityRow: Activity = {
  id: 101,
  group: 10,
  term: 1,
  title: "Ensayo del agua",
  type: "task",
  due_date: "2026-08-15",
  field: "languages",
  subject_ids: ["espanol"],
  description: "",
};

const listResponse: ActivitiesListResponse = {
  terms: [
    { id: 1, number: 1 },
    { id: 2, number: 2 },
    { id: 3, number: 3 },
  ],
  activities: [activityRow],
  stats: {
    total_activities: 1,
    graded_activities: 0,
    pending_activities: 1,
    average_score: null,
  },
};

const matrixResponse: ScoresMatrixResponse = {
  terms: listResponse.terms,
  students: [
    { id: 1, first_name: "Ana", last_name_paternal: "Lopez" },
    { id: 2, first_name: "Luis", last_name_paternal: "Perez" },
  ],
  activities: [activityRow],
  scores: [
    { student: 1, activity: 101, score: "8.5" },
    { student: 2, activity: 101, score: null },
  ],
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

function resetMocks() {
  mocks.groupId = 10;
  mocks.activitiesCalls = [];
  mocks.matrixCalls = [];
  mocks.activitiesQuery = {
    isLoading: false,
    isError: false,
    isSuccess: true,
    data: listResponse,
    isFetching: false,
  };
  mocks.matrixQuery = {
    isLoading: false,
    isError: false,
    isSuccess: true,
    data: matrixResponse,
    isFetching: false,
  };
  mocks.createMutate.mockReset();
  mocks.createMutation = { isPending: false, error: undefined };
  mocks.bulkMutate.mockReset();
  mocks.bulkMutation = { isPending: false, error: undefined };
}

function lastActivitiesArgs(): ActivitiesArgs {
  expect(mocks.activitiesCalls.length).toBeGreaterThan(0);
  return mocks.activitiesCalls[mocks.activitiesCalls.length - 1]!;
}

async function openPorAlumno(host: HTMLElement) {
  await withPeriodo(host);
  await act(async () => {
    click(btn(host, "Por alumno"));
  });
}

function scoreInput(host: HTMLElement, studentId: number, activityId: number) {
  return host.querySelector<HTMLInputElement>(
    `input[data-score-key="${studentId}:${activityId}"]`,
  );
}

describe("/actividades — Por actividad (D3)", () => {
  beforeEach(resetMocks);

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

describe("score draft helpers (D4)", () => {
  it("scoreDraftKey joins student:activity", () => {
    expect(scoreDraftKey(2, 101)).toBe("2:101");
    expect(scoreDraftKey(1, 7)).toBe("1:7");
  });

  it("displayScore keeps null empty and preserves 0.0", () => {
    expect(displayScore(null)).toBe("");
    expect(displayScore(undefined)).toBe("");
    expect(displayScore("0.0")).toBe("0.0");
    expect(displayScore("8.5")).toBe("8.5");
  });

  it("displayAverage shows em dash for null and keeps numeric strings", () => {
    expect(displayAverage(null)).toBe("—");
    expect(displayAverage(undefined)).toBe("—");
    expect(displayAverage("")).toBe("—");
    expect(displayAverage("8.3")).toBe("8.3");
  });
});

describe("/actividades — Por alumno matrix (D4)", () => {
  beforeEach(resetMocks);

  it("toggles to Por alumno and renders students × activities matrix", async () => {
    const { host, root } = await mount();
    await openPorAlumno(host);
    expect(host.textContent).toContain("Ana");
    expect(host.textContent).toContain("Lopez");
    expect(host.textContent).toContain("Luis");
    expect(host.textContent).toContain("Ensayo del agua");
    expect(scoreInput(host, 1, 101)).not.toBeNull();
    expect(scoreInput(host, 2, 101)).not.toBeNull();
    await act(async () => root.unmount());
  });

  it("shows scored value and keeps unscored null ≠ 0.0", async () => {
    const { host, root } = await mount();
    await openPorAlumno(host);
    const scored = scoreInput(host, 1, 101)!;
    const unscored = scoreInput(host, 2, 101)!;
    expect(scored.value).toBe("8.5");
    expect(unscored.value).toBe("");
    expect(unscored.value).not.toBe("0");
    expect(unscored.value).not.toBe("0.0");
    await act(async () => root.unmount());
  });

  it("renders literal 0.0 from API (distinct from unscored null)", async () => {
    mocks.matrixQuery = {
      ...mocks.matrixQuery,
      data: {
        ...matrixResponse,
        scores: [
          { student: 1, activity: 101, score: "0.0" },
          { student: 2, activity: 101, score: null },
        ],
      },
    };
    const { host, root } = await mount();
    await openPorAlumno(host);
    expect(scoreInput(host, 1, 101)!.value).toBe("0.0");
    expect(scoreInput(host, 2, 101)!.value).toBe("");
    await act(async () => root.unmount());
  });

  it("editing a cell drafts locally without calling bulk PUT", async () => {
    const { host, root } = await mount();
    await openPorAlumno(host);
    const cell = scoreInput(host, 2, 101)!;
    await act(async () => {
      typeInto(cell, "7.0");
    });
    expect(scoreInput(host, 2, 101)!.value).toBe("7.0");
    expect(mocks.bulkMutate).not.toHaveBeenCalled();
    await act(async () => root.unmount());
  });

  it("Guardar sends bulk entries keyed ${student}:${activity}", async () => {
    const { host, root } = await mount();
    await openPorAlumno(host);
    expect(btn(host, "Guardar")).toBeTruthy();
    await act(async () => {
      typeInto(scoreInput(host, 2, 101)!, "9.0");
    });
    await act(async () => {
      click(btn(host, "Guardar"));
    });
    expect(mocks.bulkMutate).toHaveBeenCalledTimes(1);
    const payload = mocks.bulkMutate.mock.calls[0]![0];
    expect(payload.group).toBe(10);
    expect(payload.entries).toEqual(
      expect.arrayContaining([{ student: 2, activity: 101, score: "9.0" }]),
    );
    // Draft Map key contract used by the UI (data-score-key)
    expect(scoreInput(host, 2, 101)!.getAttribute("data-score-key")).toBe("2:101");
    await act(async () => root.unmount());
  });

  it("null cell stays empty after draft clear without Guardar (no bulk)", async () => {
    const { host, root } = await mount();
    await openPorAlumno(host);
    const cell = scoreInput(host, 1, 101)!;
    await act(async () => {
      typeInto(cell, "");
    });
    expect(scoreInput(host, 1, 101)!.value).toBe("");
    expect(mocks.bulkMutate).not.toHaveBeenCalled();
    await act(async () => root.unmount());
  });
});

describe("/actividades — filters, stats, banner (D5)", () => {
  beforeEach(resetMocks);

  it("Periodo empty blocks fetch (termId null → query disabled)", async () => {
    expect(activitiesQueryEnabled(10, null)).toBe(false);
    expect(activitiesQueryEnabled(10, 1)).toBe(true);
    const { host, root } = await mount();
    const [group, term] = lastActivitiesArgs();
    expect(group).toBe(10);
    expect(term).toBeNull();
    expect(host.textContent).not.toContain("Ensayo del agua");
    await act(async () => root.unmount());
  });

  it("campo / asignatura / tipo / q filters are passed to the list query", async () => {
    const { host, root } = await mount();
    await withPeriodo(host);

    const fieldSelect = host.querySelector<HTMLSelectElement>("select[name='fieldFilter']");
    const subjectSelect = host.querySelector<HTMLSelectElement>("select[name='subjectFilter']");
    const typeSelect = host.querySelector<HTMLSelectElement>("select[name='typeFilter']");
    const qInput = host.querySelector<HTMLInputElement>("input[name='qFilter']");
    expect(fieldSelect).not.toBeNull();
    expect(subjectSelect).not.toBeNull();
    expect(typeSelect).not.toBeNull();
    expect(qInput).not.toBeNull();

    await act(async () => {
      typeInto(fieldSelect!, "languages");
    });
    expect(lastActivitiesArgs()[2]).toMatchObject({ field: "languages" });

    await act(async () => {
      typeInto(subjectSelect!, "espanol");
    });
    expect(lastActivitiesArgs()[2]).toMatchObject({
      field: "languages",
      subject: "espanol",
    });

    await act(async () => {
      typeInto(typeSelect!, "task");
    });
    expect(lastActivitiesArgs()[2]).toMatchObject({
      field: "languages",
      subject: "espanol",
      type: "task" as TypeEnum,
    });

    await act(async () => {
      typeInto(qInput!, "agua");
    });
    expect(lastActivitiesArgs()[2]).toMatchObject({
      field: "languages",
      subject: "espanol",
      type: "task",
      q: "agua",
    });

    await act(async () => root.unmount());
  });

  it("stats cards match API stats from the list response", async () => {
    mocks.activitiesQuery = {
      ...mocks.activitiesQuery,
      data: {
        ...listResponse,
        stats: {
          total_activities: 18,
          graded_activities: 14,
          pending_activities: 4,
          average_score: "8.3",
        },
      },
    };
    const { host, root } = await mount();
    await withPeriodo(host);
    expect(host.textContent).toMatch(/Actividades del periodo/i);
    expect(host.querySelector("[data-stat='total']")?.textContent).toBe("18");
    expect(host.textContent).toMatch(/Calificadas/i);
    expect(host.querySelector("[data-stat='graded']")?.textContent).toBe("14");
    expect(host.textContent).toMatch(/Pendientes por calificar/i);
    expect(host.querySelector("[data-stat='pending']")?.textContent).toBe("4");
    expect(host.textContent).toMatch(/Promedio de actividades/i);
    expect(host.querySelector("[data-stat='average']")?.textContent).toBe("8.3");
    await act(async () => root.unmount());
  });

  it("shows null average as em dash and different totals (triangulate stats)", async () => {
    mocks.activitiesQuery = {
      ...mocks.activitiesQuery,
      data: {
        ...listResponse,
        stats: {
          total_activities: 3,
          graded_activities: 0,
          pending_activities: 3,
          average_score: null,
        },
      },
    };
    const { host, root } = await mount();
    await withPeriodo(host);
    expect(host.querySelector("[data-stat='total']")?.textContent).toBe("3");
    expect(host.querySelector("[data-stat='graded']")?.textContent).toBe("0");
    expect(host.querySelector("[data-stat='pending']")?.textContent).toBe("3");
    expect(host.querySelector("[data-stat='average']")?.textContent).toBe("—");
    await act(async () => root.unmount());
  });

  it("Exportar and auto-save are absent; Guardar only on Por alumno after edit", async () => {
    const { host, root } = await mount();
    await withPeriodo(host);
    expect(host.textContent).not.toMatch(/Exportar/i);
    expect(host.textContent).not.toMatch(/auto-?save|guardado automático/i);
    expect(mocks.bulkMutate).not.toHaveBeenCalled();

    await act(async () => {
      click(btn(host, "Por alumno"));
    });
    await act(async () => {
      typeInto(scoreInput(host, 2, 101)!, "6.5");
    });
    expect(mocks.bulkMutate).not.toHaveBeenCalled();
    await act(async () => {
      click(btn(host, "Guardar"));
    });
    expect(mocks.bulkMutate).toHaveBeenCalledTimes(1);
    await act(async () => root.unmount());
  });

  it("Calificaciones banner is static copy and not a navigable link", async () => {
    const { host, root } = await mount();
    expect(host.textContent).toMatch(/Estas calificaciones alimentan Calificaciones/i);
    const banner = [...host.querySelectorAll("[data-banner='calificaciones']")];
    expect(banner).toHaveLength(1);
    expect(banner[0]!.querySelector("a")).toBeNull();
    expect(host.querySelector('a[href*="calificaciones"]')).toBeNull();
    await act(async () => root.unmount());
  });
});
