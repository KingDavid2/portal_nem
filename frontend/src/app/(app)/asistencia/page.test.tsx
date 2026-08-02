import { act } from "react";
import { createRoot } from "react-dom/client";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type {
  AttendanceRosterEntry,
  AttendanceStatus,
  AttendanceWeekResponse,
} from "@/lib/api/attendance";

const mocks = vi.hoisted(() => ({
  groupId: 10 as number | null,
  setGroupId: vi.fn<(id: number | null) => void>(),
  visibleGroups: [
    { id: 10, grado: 3, grupo: "A", school_year: 1, workspace: "w1" },
    { id: 11, grado: 3, grupo: "B", school_year: 1, workspace: "w1" },
  ],
  rosterQuery: {
    isLoading: false,
    isError: false,
    isSuccess: true,
    data: [] as AttendanceRosterEntry[],
  },
  weekQuery: {
    isLoading: false,
    isError: false,
    isSuccess: true,
    data: null as AttendanceWeekResponse | null,
  },
  bulkMutate: vi.fn<
    (input: unknown, opts?: { onSuccess?: () => void }) => void
  >(),
  weekBulkMutate: vi.fn<
    (input: unknown, opts?: { onSuccess?: () => void }) => void
  >(),
  bulkMutation: { isPending: false, error: undefined as unknown },
  weekBulkMutation: { isPending: false, error: undefined as unknown },
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

vi.mock("@/lib/api/attendance", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/attendance")>();
  return {
    ...actual,
    localTodayISO: () => "2026-07-29",
    useAttendanceRosterQuery: () => mocks.rosterQuery,
    useAttendanceWeekQuery: () => mocks.weekQuery,
    useAttendanceBulkMutation: () => ({
      ...mocks.bulkMutation,
      mutate: mocks.bulkMutate,
    }),
    useAttendanceWeekBulkMutation: () => ({
      ...mocks.weekBulkMutation,
      mutate: mocks.weekBulkMutate,
    }),
  };
});

import Page from "./page";

const roster: AttendanceRosterEntry[] = [
  {
    student: 1,
    first_name: "Ana",
    last_name_paternal: "López",
    curp: "LOPA010101HDFRRN01",
    status: "present",
    notes: "",
  },
  {
    student: 2,
    first_name: "Beto",
    last_name_paternal: "García",
    curp: "GARB020202HDFRRN02",
    status: "present",
    notes: "",
  },
];

const weekMatrix: AttendanceWeekResponse = {
  week_start: "2026-07-27",
  dates: [
    "2026-07-27",
    "2026-07-28",
    "2026-07-29",
    "2026-07-30",
    "2026-07-31",
  ],
  students: [
    {
      student: 1,
      first_name: "Ana",
      last_name_paternal: "López",
      days: {
        "2026-07-27": "present",
        "2026-07-28": "present",
        "2026-07-29": "present",
        "2026-07-30": "present",
        "2026-07-31": "present",
      },
    },
    {
      student: 2,
      first_name: "Beto",
      last_name_paternal: "García",
      days: {
        "2026-07-27": "present",
        "2026-07-28": "present",
        "2026-07-29": "present",
        "2026-07-30": "present",
        "2026-07-31": "present",
      },
    },
  ],
};

function statValue(host: HTMLElement, label: string) {
  const card = [...host.querySelectorAll("section")].find((section) =>
    section.textContent?.includes(label),
  );
  const strong = card?.querySelector("strong");
  return strong?.textContent ?? "";
}

function statusButton(host: HTMLElement, letter: string) {
  return [...host.querySelectorAll("button")].find(
    (button) => button.textContent?.trim() === letter,
  )!;
}

const click = (el: Element) =>
  el.dispatchEvent(new MouseEvent("click", { bubbles: true }));

function typeInto(el: HTMLInputElement, value: string) {
  Object.getOwnPropertyDescriptor(
    window.HTMLInputElement.prototype,
    "value",
  )!.set!.call(el, value);
  el.dispatchEvent(new Event("input", { bubbles: true }));
}

function selectChip(host: HTMLElement, label: string) {
  return [...host.querySelectorAll("button")].find(
    (button) => button.textContent?.trim() === label,
  )!;
}

async function mount() {
  const host = document.createElement("div");
  const root = createRoot(host);
  await act(async () => root.render(<Page />));
  return { host, root };
}

describe("/asistencia", () => {
  beforeEach(() => {
    mocks.groupId = 10;
    mocks.rosterQuery = {
      isLoading: false,
      isError: false,
      isSuccess: true,
      data: roster,
    };
    mocks.weekQuery = {
      isLoading: false,
      isError: false,
      isSuccess: true,
      data: weekMatrix,
    };
    mocks.bulkMutate.mockReset();
    mocks.weekBulkMutate.mockReset();
    mocks.bulkMutation = { isPending: false, error: undefined };
    mocks.weekBulkMutation = { isPending: false, error: undefined };
  });

  it("defaults draft rows to present and stat cards match draft counts", async () => {
    const { host, root } = await mount();
    expect(statValue(host, "Presentes")).toBe("2");
    expect(statValue(host, "Ausentes")).toBe("0");
    expect(statValue(host, "Retardos")).toBe("0");
    expect(statValue(host, "Justificados")).toBe("0");
    await act(async () => root.unmount());
  });

  it("does not call bulk API when toggling status without Guardar", async () => {
    const { host, root } = await mount();
    await act(async () => click(statusButton(host, "A")));
    expect(mocks.bulkMutate).not.toHaveBeenCalled();
    expect(statValue(host, "Ausentes")).toBe("1");
    await act(async () => root.unmount());
  });

  it("Marcar todos presentes updates draft client-side only", async () => {
    const { host, root } = await mount();
    await act(async () => click(statusButton(host, "A")));
    const markAll = [...host.querySelectorAll("button")].find((button) =>
      button.textContent?.includes("Marcar todos presentes"),
    )!;
    await act(async () => click(markAll));
    expect(statValue(host, "Presentes")).toBe("2");
    expect(mocks.bulkMutate).not.toHaveBeenCalled();
    await act(async () => root.unmount());
  });

  it("Guardar sends the full roster entries for the selected group and date", async () => {
    const { host, root } = await mount();
    const dateInput = host.querySelector<HTMLInputElement>("input[type='date']")!;
    await act(async () => typeInto(dateInput, "2026-08-01"));
    await act(async () => click(statusButton(host, "R")));
    const save = [...host.querySelectorAll("button")].find((button) =>
      button.textContent?.includes("Guardar asistencia"),
    )!;
    await act(async () => click(save));
    expect(mocks.bulkMutate).toHaveBeenCalledTimes(1);
    const payload = mocks.bulkMutate.mock.calls[0]![0] as {
      group: number;
      date: string;
      entries: { student: number; status: AttendanceStatus; notes: string }[];
    };
    expect(payload.group).toBe(10);
    expect(payload.date).toBe("2026-08-01");
    expect(payload.entries).toHaveLength(2);
    expect(payload.entries[0]).toMatchObject({ student: 1, status: "late" });
    expect(payload.entries[1]).toMatchObject({ student: 2, status: "present" });
    await act(async () => root.unmount());
  });

  it("omits Periodo and Exportar controls", async () => {
    const { host, root } = await mount();
    expect(host.textContent).not.toContain("Periodo");
    expect(host.textContent).not.toContain("Exportar");
    await act(async () => root.unmount());
  });

  it("uses group from SchoolTeachingContext and local YYYY-MM-DD date input", async () => {
    const { host, root } = await mount();
    const groupSelect = host.querySelector<HTMLSelectElement>("select")!;
    expect(groupSelect.value).toBe("10");
    const dateInput = host.querySelector<HTMLInputElement>("input[type='date']")!;
    expect(dateInput.value).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    await act(async () => root.unmount());
  });

  it("toggles to Semanal and shows weekday headers without CURP or Observación", async () => {
    const { host, root } = await mount();
    await act(async () => click(selectChip(host, "Semanal")));
    expect(host.textContent).toContain("Asistencia semanal");
    expect(host.textContent).toContain("Lun 27");
    expect(host.textContent).toContain("Vie 31");
    expect(host.textContent).not.toContain("CURP");
    expect(host.textContent).not.toContain("Observación");
    expect(statValue(host, "Presentes")).toBe("10");
    await act(async () => root.unmount());
  });

  it("Semanal select change stays draft until Guardar week bulk", async () => {
    const { host, root } = await mount();
    await act(async () => click(selectChip(host, "Semanal")));
    const cellSelect = host.querySelectorAll("select")[1] as HTMLSelectElement;
    await act(async () => {
      cellSelect.value = "absent";
      cellSelect.dispatchEvent(new Event("change", { bubbles: true }));
    });
    expect(mocks.weekBulkMutate).not.toHaveBeenCalled();
    expect(statValue(host, "Ausentes")).toBe("1");
    const save = [...host.querySelectorAll("button")].find((button) =>
      button.textContent?.includes("Guardar asistencia"),
    )!;
    await act(async () => click(save));
    expect(mocks.weekBulkMutate).toHaveBeenCalledTimes(1);
    const payload = mocks.weekBulkMutate.mock.calls[0]![0] as {
      group: number;
      week_start: string;
      entries: { student: number; date: string; status: AttendanceStatus }[];
    };
    expect(payload.group).toBe(10);
    expect(payload.week_start).toBe("2026-07-27");
    expect(payload.entries).toHaveLength(10);
    expect(
      payload.entries.find(
        (entry) => entry.student === 1 && entry.date === "2026-07-27",
      ),
    ).toMatchObject({ status: "absent" });
    await act(async () => root.unmount());
  });
});
