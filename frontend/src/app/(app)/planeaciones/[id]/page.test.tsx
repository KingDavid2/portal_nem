import { act } from "react"; import { createRoot } from "react-dom/client"; import { beforeEach, describe, expect, it, vi } from "vitest";
const mocks=vi.hoisted(()=>({query:{isLoading:true,isError:false,data:undefined as unknown},mutate:vi.fn(),push:vi.fn(),export:vi.fn()}));
vi.mock("next/navigation",()=>({useRouter:()=>({push:mocks.push})}));
// `lessonPlanCreateInput` is kept real: the regenerate body it derives is
// exactly what these tests assert on.
vi.mock("@/lib/api/lesson-plans",async(importActual)=>({...await importActual<object>(),useLessonPlanQuery:()=>mocks.query,useCreateLessonPlanMutation:()=>({mutate:mocks.mutate,isPending:false})}));
vi.mock("@/lib/api/lesson-plan-export",()=>({downloadLessonPlanExport:mocks.export})); vi.mock("../proyecto-viewer",()=>({ProyectoViewer:()=> <div>Proyecto viewer</div>}));
import Page from "./page";
/** Project context the backend persists, as a regenerable plan carries it. */
const context={field_id:"languages",subject_id:"spanish",methodology_id:"community-based-project-learning",context_diagnosis:"Diagnóstico",scenario:"community",duration_weeks:4,start_date:"2026-01-12",end_date:"2026-02-06",cross_cutting_theme_ids:["critical-thinking"],content_selections:[{content_id:"languages-text-resources",pda_ids:["languages-accentuation"]}]};
async function mount(){const host=document.createElement("div");const root=createRoot(host);await act(async()=>root.render(<Page params={Promise.resolve({id:"7"})}/>));return{host,root}}
describe("Planeacion detail",()=>{beforeEach(()=>{mocks.query={isLoading:true,isError:false,data:undefined};mocks.mutate.mockReset();mocks.push.mockReset();mocks.export.mockReset()});it("shows loading",async()=>{const {host,root}=await mount();expect(host.textContent).toContain("Cargando planeación");await act(async()=>root.unmount())});it("shows legacy invented PDA warning when list is empty",async()=>{mocks.query={isLoading:false,isError:false,data:{id:7,status:"ready",invented_pdas:true,invented_pda_texts:[],group:1,campo:"L",grade:"1",theme:"T",proyecto:{},...context}};const {host,root}=await mount();expect(host.textContent).toContain("al menos un PDA que no está en el conjunto fuente");await act(async()=>root.unmount())});it("lists invented PDA texts verbatim in the alert",async()=>{mocks.query={isLoading:false,isError:false,data:{id:7,status:"ready",invented_pdas:true,invented_pda_texts:["El alumno analiza la estructura del cuento.","El alumno identifica el tema principal."],group:1,campo:"L",grade:"1",theme:"T",proyecto:{},...context}};const {host,root}=await mount();expect(host.textContent).toContain("El alumno analiza la estructura del cuento.");expect(host.textContent).toContain("El alumno identifica el tema principal.");await act(async()=>root.unmount())});});

it("exports the ready plan and surfaces export failures", async () => {
  mocks.query={isLoading:false,isError:false,data:{id:7,status:"ready",invented_pdas:false,invented_pda_texts:[],group:1,campo:"L",grade:"1",theme:"T",proyecto:{},...context}};
  mocks.export.mockRejectedValue(new Error("export failed"));
  const {host,root}=await mount();
  const exportButton=[...host.querySelectorAll("button")].find((button)=>button.textContent?.includes("Exportar"))!;
  await act(async()=>exportButton.dispatchEvent(new MouseEvent("click",{bubbles:true})));
  expect(mocks.export).toHaveBeenCalledWith(7,"docx"); expect(host.textContent).toContain("export failed");
  await act(async()=>root.unmount());
});

it("shows failed state and redirects after regeneration succeeds", async () => {
  mocks.query={isLoading:false,isError:false,data:{id:7,status:"failed",failure_reason:"detalle",group:1,campo:"L",grade:"1",theme:"T",proyecto:{},...context}};
  const {host,root}=await mount();
  expect(host.textContent).toContain("La generación falló: detalle");
  await act(async()=>host.querySelector("button")!.dispatchEvent(new MouseEvent("click",{bubbles:true})));
  const [body, options]=mocks.mutate.mock.calls[0];
  expect(body).toEqual({group:1,theme:"T",...context});
  await act(async()=>options.onSuccess({id:9}));
  expect(mocks.push).toHaveBeenCalledWith("/planeaciones/9");
  await act(async()=>root.unmount());
});

it("does not offer regeneration for plans without persisted context", async () => {
  // Reset explicitly: the `beforeEach` above is scoped to its `describe`.
  mocks.mutate.mockReset();
  mocks.query={isLoading:false,isError:false,data:{id:7,status:"failed",failure_reason:"detalle",group:1,campo:"L",grade:"1",theme:"T",proyecto:{},...context,field_id:"",duration_weeks:null,start_date:null,end_date:null}};
  const {host,root}=await mount();
  const retry=host.querySelector("button")!;
  expect(retry.disabled).toBe(true);
  // A disabled button with no explanation is a dead end — say why.
  expect(host.textContent).toContain("se creó antes del formulario actual");
  await act(async()=>retry.dispatchEvent(new MouseEvent("click",{bubbles:true})));
  expect(mocks.mutate).not.toHaveBeenCalled();
  await act(async()=>root.unmount());
});

it("explains the disabled regenerate button on a ready legacy plan", async () => {
  mocks.query={isLoading:false,isError:false,data:{id:7,status:"ready",invented_pdas:false,invented_pda_texts:[],group:1,campo:"L",grade:"1",theme:"T",proyecto:{},...context,field_id:"",duration_weeks:null,start_date:null,end_date:null}};
  const {host,root}=await mount();
  const regenerate=[...host.querySelectorAll("button")].find((button)=>button.textContent?.includes("Regenerar"))!;
  expect(regenerate.disabled).toBe(true);
  expect(host.textContent).toContain("se creó antes del formulario actual");
  await act(async()=>root.unmount());
});

it("says nothing about regeneration when the plan carries its context", async () => {
  mocks.query={isLoading:false,isError:false,data:{id:7,status:"ready",invented_pdas:false,invented_pda_texts:[],group:1,campo:"L",grade:"1",theme:"T",proyecto:{},...context}};
  const {host,root}=await mount();
  const regenerate=[...host.querySelectorAll("button")].find((button)=>button.textContent?.includes("Regenerar"))!;
  expect(regenerate.disabled).toBe(false);
  expect(host.textContent).not.toContain("se creó antes del formulario actual");
  await act(async()=>root.unmount());
});
