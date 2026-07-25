import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Card } from "./card";
import { FormField } from "./form-field";
import { Avatar } from "./avatar";
import { StatusChip } from "./status-chip";
import { Select } from "./select";

describe("display primitives", () => {
  it("forwards native props and presents form feedback", () => {
    const html = renderToStaticMarkup(<><Card className="custom" data-id="card">Body</Card><FormField label="Correo" required error="Inválido"><input id="email" name="email" /></FormField><Avatar name="Ana Pérez" /><StatusChip tone="success">Activo</StatusChip></>);
    expect(html).toContain("custom"); expect(html).toContain('data-id="card"'); expect(html).toContain("Correo"); expect(html).toContain("Inválido"); expect(html).toContain('for="email"'); expect(html).toContain("AP"); expect(html).toContain("Activo");
  });
});

describe("Select", () => {
  it("renders its options and stays associated with a FormField label", () => {
    const html = renderToStaticMarkup(
      <FormField id="campo" label="Campo formativo">
        <Select defaultValue="lenguajes"><option value="lenguajes">Lenguajes</option><option value="etica">Ética</option></Select>
      </FormField>,
    );
    expect(html).toContain('for="campo"'); expect(html).toContain('id="campo"'); expect(html).toContain("Lenguajes"); expect(html).toContain("Ética");
  });

  it("respects disabled and forwards the ref to the native select", async () => {
    const { act } = await import("react");
    const { createRoot } = await import("react-dom/client");
    const host = document.createElement("div");
    const root = createRoot(host);
    const ref = { current: null as HTMLSelectElement | null };
    await act(async () => root.render(<Select ref={ref} disabled defaultValue="a"><option value="a">A</option></Select>));
    expect(ref.current).toBe(host.querySelector("select"));
    expect(ref.current!.disabled).toBe(true);
    expect(ref.current!.value).toBe("a");
    await act(async () => root.unmount());
  });
});
