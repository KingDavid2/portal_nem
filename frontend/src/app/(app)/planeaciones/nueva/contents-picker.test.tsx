import { act } from "react";
import { createRoot } from "react-dom/client";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ContentsPicker } from "./contents-picker";
import type { CatalogContent } from "@/lib/api/lesson-plan-catalog";
import type { ContentSelection } from "./use-new-plan-form";

const mockContents: CatalogContent[] = [
  {
    id: "c1",
    text: "Comprensión de textos literarios",
    pdas: [
      { id: "p1", text: "Identifica el tema central" },
      { id: "p2", text: "Infiere el significado de palabras" },
      { id: "p3", text: "Compara personajes" },
    ],
  },
  {
    id: "c2",
    text: "Producción de textos informativos",
    pdas: [
      { id: "p4", text: "Organiza ideas en párrafos" },
      { id: "p5", text: "Usa conectores textuales" },
    ],
  },
  {
    id: "c3",
    text: "Argumentación oral",
    pdas: [
      { id: "p6", text: "Presenta una opinión" },
    ],
  },
];

const initialSelections: ContentSelection[] = [
  { content_id: "c1", pda_ids: ["p1"] },
];

function mountPicker() {
  const host = document.createElement("div");
  const root = createRoot(host);
  return { host, root };
}

/** Types into a controlled input the way React sees it. Assigning `.value`
 * directly is swallowed: React caches the last value on the node and treats an
 * event whose value it already knows as a no-op, so `onChange` never fires.
 * Going through the prototype's setter updates the DOM without touching that
 * cache, and the dispatched `input` event then reads as a genuine change. */
function typeInto(input: HTMLInputElement, value: string) {
  const setValue = Object.getOwnPropertyDescriptor(
    window.HTMLInputElement.prototype,
    "value",
  )!.set!;
  setValue.call(input, value);
  input.dispatchEvent(new Event("input", { bubbles: true }));
}

const contentTitles = (host: HTMLElement) =>
  [...host.querySelectorAll("h3")].map((heading) => heading.textContent);

describe("ContentsPicker", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("checks a PDA and the footer count reflects it", async () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    const { host, root } = mountPicker();

    await act(async () => { root.render(<ContentsPicker contents={mockContents} selections={initialSelections} onConfirm={onConfirm} onCancel={onCancel} />); });

    const allCheckboxes = host.querySelectorAll<HTMLInputElement>('input[type="checkbox"]');
    const pdaCheckboxes = [...allCheckboxes].filter((c) => c.getAttribute("aria-label") === "Seleccionar PDA");
    expect(pdaCheckboxes[0].checked).toBe(true); // p1 already checked from initialSelections
    expect(pdaCheckboxes[1].checked).toBe(false); // p2 not yet checked

    await act(async () => {
      pdaCheckboxes[1].dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    expect(host.textContent).toContain("2 PDAs seleccionados");

    await act(async () => { root.unmount(); });
  });

  it("unchecks the last PDA of a content and that content drops", async () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    const { host, root } = mountPicker();

    await act(async () => { root.render(<ContentsPicker contents={mockContents} selections={initialSelections} onConfirm={onConfirm} onCancel={onCancel} />); });

    const allCheckboxes = host.querySelectorAll<HTMLInputElement>('input[type="checkbox"]');
    const pdaCheckboxes = [...allCheckboxes].filter((c) => c.getAttribute("aria-label") === "Seleccionar PDA");

    await act(async () => {
      pdaCheckboxes[0].dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    expect(host.textContent).toContain("0 PDAs seleccionados");

    await act(async () => { root.unmount(); });
  });

  it('"Usar estos contenidos" calls onConfirm with the draft and "Cancelar" calls onCancel', async () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    const { host, root } = mountPicker();

    await act(async () => { root.render(<ContentsPicker contents={mockContents} selections={initialSelections} onConfirm={onConfirm} onCancel={onCancel} />); });

    const buttons = [...host.querySelectorAll("button")];
    const cancelBtn = buttons.find((b) => b.textContent?.includes("Cancelar"));
    const useBtn = buttons.find((b) => b.textContent?.includes("Usar"));

    await act(async () => {
      cancelBtn!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
    expect(onCancel).toHaveBeenCalled();
    expect(onConfirm).not.toHaveBeenCalled();

    onConfirm.mockReset();
    onCancel.mockReset();

    const allCheckboxes = host.querySelectorAll<HTMLInputElement>('input[type="checkbox"]');
    const pdaCheckboxes = [...allCheckboxes].filter((c) => c.getAttribute("aria-label") === "Seleccionar PDA");
    await act(async () => {
      pdaCheckboxes[1].dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    await act(async () => {
      useBtn!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onConfirm).toHaveBeenCalledWith([
      { content_id: "c1", pda_ids: ["p1", "p2"] },
    ]);
    expect(onCancel).not.toHaveBeenCalled();

    await act(async () => { root.unmount(); });
  });

  it("the search input filters the list by content text, case-insensitively", async () => {
    const { host, root } = mountPicker();
    await act(async () => { root.render(<ContentsPicker contents={mockContents} selections={initialSelections} onConfirm={vi.fn()} onCancel={vi.fn()} />); });

    expect(contentTitles(host)).toHaveLength(3);

    const search = host.querySelector<HTMLInputElement>('input[type="search"]')!;
    await act(async () => { typeInto(search, "INFORMATIVOS"); });
    expect(contentTitles(host)).toEqual(["Producción de textos informativos"]);

    // Whitespace is not a query: clearing restores the full list.
    await act(async () => { typeInto(search, "   "); });
    expect(contentTitles(host)).toHaveLength(3);

    await act(async () => { root.unmount(); });
  });

  it("the search input also matches PDA text", async () => {
    const { host, root } = mountPicker();
    await act(async () => { root.render(<ContentsPicker contents={mockContents} selections={initialSelections} onConfirm={vi.fn()} onCancel={vi.fn()} />); });

    const search = host.querySelector<HTMLInputElement>('input[type="search"]')!;
    await act(async () => { typeInto(search, "conectores"); });
    expect(contentTitles(host)).toEqual(["Producción de textos informativos"]);

    await act(async () => { typeInto(search, "noexiste"); });
    expect(contentTitles(host)).toHaveLength(0);

    await act(async () => { root.unmount(); });
  });

  it("a search filter hides rows without changing the counts or what is committed", async () => {
    const onConfirm = vi.fn();
    const { host, root } = mountPicker();
    await act(async () => { root.render(<ContentsPicker contents={mockContents} selections={initialSelections} onConfirm={onConfirm} onCancel={vi.fn()} />); });

    // Select a PDA from a content the upcoming query will hide.
    const pdas = () => [...host.querySelectorAll<HTMLInputElement>('input[type="checkbox"]')]
      .filter((box) => box.getAttribute("aria-label") === "Seleccionar PDA");
    await act(async () => { pdas()[3].dispatchEvent(new MouseEvent("click", { bubbles: true })); });
    expect(host.textContent).toContain("2 contenidos · 2 PDAs seleccionados");

    const search = host.querySelector<HTMLInputElement>('input[type="search"]')!;
    await act(async () => { typeInto(search, "Argumentación"); });

    // Only one card is visible, but the draft still holds both picks — the
    // footer must report the draft, not the visible subset.
    expect(contentTitles(host)).toEqual(["Argumentación oral"]);
    expect(host.textContent).toContain("2 contenidos · 2 PDAs seleccionados");
    expect(host.textContent).toContain("2 / 6");

    const useBtn = [...host.querySelectorAll("button")].find((b) => b.textContent?.includes("Usar"));
    await act(async () => { useBtn!.dispatchEvent(new MouseEvent("click", { bubbles: true })); });
    expect(onConfirm).toHaveBeenCalledWith([
      { content_id: "c1", pda_ids: ["p1"] },
      { content_id: "c2", pda_ids: ["p4"] },
    ]);

    await act(async () => { root.unmount(); });
  });

  it("a click inside the panel does not dismiss the picker", async () => {
    const onCancel = vi.fn();
    const { host, root } = mountPicker();
    await act(async () => { root.render(<ContentsPicker contents={mockContents} selections={initialSelections} onConfirm={vi.fn()} onCancel={onCancel} />); });

    const dialog = host.querySelector<HTMLElement>("[role='dialog']")!;
    await act(async () => { dialog.dispatchEvent(new MouseEvent("click", { bubbles: true })); });
    expect(onCancel).not.toHaveBeenCalled();

    await act(async () => { root.unmount(); });
  });

  it("empty contents renders the no-contents message", async () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    const { host, root } = mountPicker();

    await act(async () => { root.render(<ContentsPicker contents={[]} selections={[]} onConfirm={onConfirm} onCancel={onCancel} />); });

    expect(host.textContent).toContain("Aún no hay contenidos verificados para este campo.");

    await act(async () => { root.unmount(); });
  });

  it("Escape key calls onCancel", async () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    const { root } = mountPicker();

    await act(async () => { root.render(<ContentsPicker contents={mockContents} selections={initialSelections} onConfirm={onConfirm} onCancel={onCancel} />); });

    await act(async () => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    });

    expect(onCancel).toHaveBeenCalled();
    expect(onConfirm).not.toHaveBeenCalled();

    await act(async () => { root.unmount(); });
  });

  it("renders with correct ARIA attributes", async () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    const { host, root } = mountPicker();

    await act(async () => { root.render(<ContentsPicker contents={mockContents} selections={initialSelections} onConfirm={onConfirm} onCancel={onCancel} />); });

    const dialog = host.querySelector<HTMLDivElement>("[role='dialog']");
    expect(dialog?.getAttribute("role")).toBe("dialog");
    expect(dialog?.getAttribute("aria-modal")).toBe("true");
    expect(dialog?.getAttribute("aria-label")).toBe("Contenidos y PDAs");

    await act(async () => { root.unmount(); });
  });
});