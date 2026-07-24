import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ContenidoCard } from "./contenido-card"; import { MomentoCard } from "./momento-card";
describe("composite cards", () => { it("composes supplied rows and slots", () => { const html=renderToStaticMarkup(<><ContenidoCard title="Contenido" actions={<button>Editar</button>} pdaRows={[{ id: "a", content: "PDA real", selected: true, featured: true }]}><p>Detalle</p></ContenidoCard><MomentoCard title="Inicio" subtitle="Clase" status={<span>Listo</span>} pasoRows={[{ number: 7, content: "Paso real" }]}><p>Cuerpo</p></MomentoCard></>); expect(html).toContain("PDA real"); expect(html).toContain("Paso real"); expect(html).toContain("Editar"); expect(html).toContain("Listo"); }); });
