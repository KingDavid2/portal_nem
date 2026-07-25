import { act } from "react";
import { createRoot } from "react-dom/client";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SummaryPanel } from "./summary-panel";
import type { GenerationQuota } from "@/lib/api/lesson-plan-catalog";

type Props = React.ComponentProps<typeof SummaryPanel>;

function makeProps(overrides: Partial<Props> = {}): Props {
  return {
    methodologyName: "ABP Comunitario",
    durationWeeks: 3,
    pdaCount: 4,
    ejeCount: 2,
    pendingRequirements: [],
    submitAllowed: true,
    onSubmit: vi.fn(),
    isPending: false,
    quota: undefined,
    errorMessage: undefined,
    ...overrides,
  };
}

function mount(props: Props) {
  const host = document.createElement("div");
  const root = createRoot(host);
  return {
    host,
    root,
    render: () =>
      act(async () => {
        root.render(<SummaryPanel {...props} />);
      }),
    unmount: () => act(async () => { root.unmount(); }),
  };
}

describe("SummaryPanel", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the title and the three notes", async () => {
    const { host, render, unmount } = mount(makeProps());
    await render();
    expect(host.textContent).toContain("Lo que se va a generar");
    expect(host.textContent).toContain(
      "PDAs, contenidos y ejes se toman tal cual del programa sintético.",
    );
    expect(host.textContent).toContain(
      "La IA solo redacta los momentos, pasos y dinámicas alrededor de ellos.",
    );
    expect(host.textContent).toContain("Todo queda editable antes de que lo apruebes.");
    await unmount();
  });

  it("renders methodology, structure, duration, PDA and eje counts", async () => {
    const { host, render, unmount } = mount(makeProps());
    await render();
    expect(host.textContent).toContain("ABP Comunitario");
    expect(host.textContent).toContain("3 fases · 11 momentos");
    expect(host.textContent).toContain("3 semanas");
    expect(host.textContent).toContain("4 seleccionados"); // PDAs
    expect(host.textContent).toContain("2 seleccionados"); // Ejes
    await unmount();
  });

  it("shows em-dash for methodology when absent", async () => {
    const { host, render, unmount } = mount(makeProps({ methodologyName: undefined }));
    await render();
    expect(host.textContent).toContain("—");
    await unmount();
  });

  it("CTA is disabled when submit is not allowed, and says what is missing", async () => {
    const { host, render, unmount } = mount(
      makeProps({
        submitAllowed: false,
        pendingRequirements: ["Selecciona un grupo.", "Selecciona al menos un contenido."],
      }),
    );
    await render();
    const btn = host.querySelector<HTMLButtonElement>("button");
    expect(btn!.disabled).toBe(true);
    expect(host.textContent).toContain("Falta por completar");
    expect([...host.querySelectorAll("li")].map((item) => item.textContent)).toEqual([
      "Selecciona un grupo.",
      "Selecciona al menos un contenido.",
    ]);
    await unmount();
  });

  it("no requirements list is rendered once the form is complete", async () => {
    const { host, render, unmount } = mount(makeProps({ pendingRequirements: [] }));
    await render();
    expect(host.textContent).not.toContain("Falta por completar");
    await unmount();
  });

  it("CTA is enabled when submit is allowed and calls the handler once", async () => {
    const handler = vi.fn();
    const { host, render, unmount } = mount(
      makeProps({ submitAllowed: true, onSubmit: handler }),
    );
    await render();
    const btn = host.querySelector<HTMLButtonElement>("button");
    expect(btn!.disabled).toBe(false);

    await act(async () => {
      btn!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
    expect(handler).toHaveBeenCalledTimes(1);
    await unmount();
  });

  it("CTA is disabled while mutation is pending", async () => {
    const { host, render, unmount } = mount(makeProps({ isPending: true }));
    await render();
    const btn = host.querySelector<HTMLButtonElement>("button");
    expect(btn!.disabled).toBe(true);
    await unmount();
  });

  it("quota block is absent when quota is undefined", async () => {
    const { host, render, unmount } = mount(makeProps({ quota: undefined }));
    await render();
    expect(host.textContent).not.toContain("Generaciones de este mes");
    await unmount();
  });

  it("quota block renders 3 de 20 with correct progressbar ARIA", async () => {
    const quota: GenerationQuota = {
      period: "2026-07",
      used: 3,
      limit: 20,
      remaining: 17,
    };
    const { host, render, unmount } = mount(makeProps({ quota }));
    await render();
    expect(host.textContent).toContain("Generaciones de este mes");
    expect(host.textContent).toContain("3 de 20");

    const bar = host.querySelector<HTMLElement>('[role="progressbar"]');
    expect(bar).not.toBeNull();
    expect(bar!.getAttribute("aria-valuenow")).toBe("3");
    expect(bar!.getAttribute("aria-valuemin")).toBe("0");
    expect(bar!.getAttribute("aria-valuemax")).toBe("20");
    expect(bar!.firstElementChild).toHaveProperty("style.width", "15%");
    await unmount();
  });

  it("a zero limit empties the bar instead of dividing by zero", async () => {
    const quota: GenerationQuota = {
      period: "2026-07",
      used: 0,
      limit: 0,
      remaining: 0,
    };
    const { host, render, unmount } = mount(makeProps({ quota }));
    await render();
    // `NaN` from `0 / 0` would land in the inline style, never in the text, so
    // asserting on `textContent` here would pass while the bar was broken.
    expect(host.innerHTML).not.toContain("NaN");
    const bar = host.querySelector<HTMLElement>('[role="progressbar"]');
    expect(bar!.firstElementChild).toHaveProperty("style.width", "0%");
    await unmount();
  });

  it("error message renders in a destructive block", async () => {
    const { host, render, unmount } = mount(
      makeProps({ errorMessage: "Something went wrong" }),
    );
    await render();
    expect(host.textContent).toContain("Something went wrong");
    await unmount();
  });
});