import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ChoiceChip } from "./choice-chip";

let container: HTMLDivElement;
let root: Root;

beforeEach(() => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
});

function render(ui: React.ReactNode) {
  act(() => root.render(ui));
  return container.querySelector("button") as HTMLButtonElement;
}

describe("ChoiceChip", () => {
  it("reports the toggled value to the change callback on click", () => {
    const onSelectedChange = vi.fn();
    const chip = render(<ChoiceChip variant="multi" onSelectedChange={onSelectedChange}>Inclusión</ChoiceChip>);

    act(() => chip.click());

    expect(onSelectedChange).toHaveBeenCalledWith(true);
  });

  it("reports deselection when an already selected chip is clicked", () => {
    const onSelectedChange = vi.fn();
    const chip = render(<ChoiceChip selected onSelectedChange={onSelectedChange}>Aula</ChoiceChip>);

    act(() => chip.click());

    expect(onSelectedChange).toHaveBeenCalledWith(false);
  });

  it("exposes the selected state to assistive technology", () => {
    expect(render(<ChoiceChip>Aula</ChoiceChip>).getAttribute("aria-pressed")).toBe("false");
    expect(render(<ChoiceChip selected>Aula</ChoiceChip>).getAttribute("aria-pressed")).toBe("true");
  });

  it("renders a plus icon while the multi-select chip is unselected", () => {
    const chip = render(<ChoiceChip variant="multi">Inclusión</ChoiceChip>);

    expect(chip.querySelector("svg")?.getAttribute("class")).toContain("lucide-plus");
  });

  it("renders a check icon while the multi-select chip is selected", () => {
    const chip = render(<ChoiceChip variant="multi" selected>Inclusión</ChoiceChip>);

    expect(chip.querySelector("svg")?.getAttribute("class")).toContain("lucide-check");
  });

  it("renders no icon for the single-select chip in either state", () => {
    expect(render(<ChoiceChip>Aula</ChoiceChip>).querySelector("svg")).toBeNull();
    expect(render(<ChoiceChip selected>Aula</ChoiceChip>).querySelector("svg")).toBeNull();
  });

  it("does not report changes while disabled", () => {
    const onSelectedChange = vi.fn();
    const chip = render(<ChoiceChip disabled onSelectedChange={onSelectedChange}>Aula</ChoiceChip>);

    act(() => chip.click());

    expect(chip.disabled).toBe(true);
    expect(onSelectedChange).not.toHaveBeenCalled();
  });

  it("stays reachable by keyboard as a real button", () => {
    const chip = render(<ChoiceChip variant="multi">Inclusión</ChoiceChip>);

    chip.focus();

    expect(chip.tagName).toBe("BUTTON");
    expect(chip.type).toBe("button");
    expect(chip.tabIndex).toBe(0);
    expect(document.activeElement).toBe(chip);
  });
});
