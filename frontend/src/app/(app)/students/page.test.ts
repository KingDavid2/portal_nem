import { readFileSync } from "node:fs"; import { resolve } from "node:path"; import { describe, expect, it } from "vitest";
const page=readFileSync(resolve(process.cwd(),"src/app/(app)/students/page.tsx"),"utf8");
describe("StudentsPage data truth",()=>{it("does not fabricate an active status absent from the Student model",()=>{expect(page).not.toContain('StatusChip');expect(page).not.toContain('>Activo<');});});
