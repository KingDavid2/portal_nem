import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { StudentForm } from "./student-form";
describe("StudentForm",()=>{it("uses associated field controls while preserving submit payload",()=>{const html=renderToStaticMarkup(<StudentForm groupId={3} errorMessage="Error actual" isPending={false} onSubmit={vi.fn()}/>);expect(html).toContain('for="student-first-name"');expect(html).toContain("Error actual");expect(html).toContain("Crear alumno");});});
