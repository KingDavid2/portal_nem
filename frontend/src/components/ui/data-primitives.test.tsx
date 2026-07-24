import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { StatCard } from "./stat-card"; import { EstadoButton } from "./estado-button"; import { PdaRow } from "./pda-row"; import { PasoRow } from "./paso-row";
describe("data primitives", () => { it("renders supplied content and selection state", () => { const html=renderToStaticMarkup(<><StatCard label="Alumnos" value="12" tone="success" /><EstadoButton selected>Activo</EstadoButton><PdaRow selected>Contenido</PdaRow><PasoRow number={2}>Paso real</PasoRow></>); expect(html).toContain("Alumnos"); expect(html).toContain("12"); expect(html).toContain("Activo"); expect(html).toContain("Contenido"); expect(html).toContain("Paso real"); }); });

it("calls onSelectedChange from the real PDA checkbox", async () => {
  const { act } = await import("react");
  const { createRoot } = await import("react-dom/client");
  const host = document.createElement("div");
  const selected: boolean[] = [];
  const root = createRoot(host);
  await act(async () => root.render(<PdaRow onSelectedChange={(value) => selected.push(value)}>PDA</PdaRow>));
  const input = host.querySelector("input")!;
  await act(async () => input.dispatchEvent(new MouseEvent("click", { bubbles: true })));
  expect(selected).toEqual([true]);
  await act(async () => root.unmount());
});
