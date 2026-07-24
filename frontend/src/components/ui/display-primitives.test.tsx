import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Card } from "./card";
import { FormField } from "./form-field";
import { Avatar } from "./avatar";
import { StatusChip } from "./status-chip";

describe("display primitives", () => {
  it("forwards native props and presents form feedback", () => {
    const html = renderToStaticMarkup(<><Card className="custom" data-id="card">Body</Card><FormField label="Correo" required error="Inválido"><input id="email" name="email" /></FormField><Avatar name="Ana Pérez" /><StatusChip tone="success">Activo</StatusChip></>);
    expect(html).toContain("custom"); expect(html).toContain('data-id="card"'); expect(html).toContain("Correo"); expect(html).toContain("Inválido"); expect(html).toContain('for="email"'); expect(html).toContain("AP"); expect(html).toContain("Activo");
  });
});
