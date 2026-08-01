import { act } from "react";
import { createRoot } from "react-dom/client";
import { describe, expect, it, vi } from "vitest";
import { SchoolContextFilters } from "./school-context-filters";

describe("SchoolContextFilters", () => {
  it("notifies only onSchoolChange when school changes (parent owns cascade)", async () => {
    const onSchoolChange = vi.fn();
    const onYearChange = vi.fn();
    const onGroupChange = vi.fn();
    const host = document.createElement("div");
    const root = createRoot(host);
    await act(async () =>
      root.render(
        <SchoolContextFilters
          schools={[{ id: 1, label: "Escuela" }]}
          schoolYears={[{ id: 2, label: "2024-2025" }]}
          groups={[{ id: 3, label: "1A" }]}
          schoolId={1}
          schoolYearId={2}
          groupId={3}
          onSchoolChange={onSchoolChange}
          onSchoolYearChange={onYearChange}
          onGroupChange={onGroupChange}
        />,
      ),
    );
    const selects = host.querySelectorAll("select");
    await act(async () => {
      Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value")!.set!.call(
        selects[0],
        "",
      );
      selects[0]!.dispatchEvent(new Event("change", { bubbles: true }));
    });
    expect(onSchoolChange).toHaveBeenCalledWith(null);
    expect(onYearChange).not.toHaveBeenCalled();
    expect(onGroupChange).not.toHaveBeenCalled();
    await act(async () => root.unmount());
  });

  it("clears group when ciclo changes", async () => {
    const onSchoolChange = vi.fn();
    const onYearChange = vi.fn();
    const onGroupChange = vi.fn();
    const host = document.createElement("div");
    const root = createRoot(host);
    await act(async () =>
      root.render(
        <SchoolContextFilters
          schools={[{ id: 1, label: "Escuela" }]}
          schoolYears={[
            { id: 2, label: "2024-2025" },
            { id: 4, label: "2025-2026" },
          ]}
          groups={[{ id: 3, label: "1A" }]}
          schoolId={1}
          schoolYearId={2}
          groupId={3}
          onSchoolChange={onSchoolChange}
          onSchoolYearChange={onYearChange}
          onGroupChange={onGroupChange}
        />,
      ),
    );
    const selects = host.querySelectorAll("select");
    await act(async () => {
      Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value")!.set!.call(
        selects[1],
        "4",
      );
      selects[1]!.dispatchEvent(new Event("change", { bubbles: true }));
    });
    expect(onYearChange).toHaveBeenCalledWith(4);
    expect(onGroupChange).toHaveBeenCalledWith(null);
    expect(onSchoolChange).not.toHaveBeenCalled();
    await act(async () => root.unmount());
  });
});
