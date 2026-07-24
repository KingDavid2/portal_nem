import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { SchoolForm } from "./school-form";
describe("SchoolForm",()=>{it("uses associated shared field controls and preserves errors",()=>{const html=renderToStaticMarkup(<SchoolForm errorMessage="Error actual" isPending={false} onSubmit={vi.fn()}/>);expect(html).toContain('for="school-name"');expect(html).toContain("Error actual");expect(html).toContain("Crear escuela");});});
