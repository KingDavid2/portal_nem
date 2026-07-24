import { act } from "react"; import { createRoot } from "react-dom/client"; import { beforeEach, describe, expect, it, vi } from "vitest";
const mocks=vi.hoisted(()=>({query:{isLoading:true,isError:false,data:undefined as unknown},mutate:vi.fn(),push:vi.fn(),export:vi.fn()}));
vi.mock("next/navigation",()=>({useRouter:()=>({push:mocks.push})})); vi.mock("@/lib/api/lesson-plans",()=>({useLessonPlanQuery:()=>mocks.query,useCreateLessonPlanMutation:()=>({mutate:mocks.mutate,isPending:false})})); vi.mock("@/lib/api/lesson-plan-export",()=>({downloadLessonPlanExport:mocks.export})); vi.mock("../proyecto-viewer",()=>({ProyectoViewer:()=> <div>Proyecto viewer</div>}));
import Page from "./page";
async function mount(){const host=document.createElement("div");const root=createRoot(host);await act(async()=>root.render(<Page params={Promise.resolve({id:"7"})}/>));return{host,root}}
describe("Planeacion detail",()=>{beforeEach(()=>{mocks.query={isLoading:true,isError:false,data:undefined};mocks.mutate.mockReset();mocks.push.mockReset();mocks.export.mockReset()});it("shows loading",async()=>{const {host,root}=await mount();expect(host.textContent).toContain("Cargando planeación");await act(async()=>root.unmount())});it("shows invented PDA warning for ready plans",async()=>{mocks.query={isLoading:false,isError:false,data:{id:7,status:"ready",invented_pdas:true,group:1,campo:"L",grade:"1",theme:"T",proyecto:{}}};const {host,root}=await mount();expect(host.textContent).toContain("posible invención");await act(async()=>root.unmount())});});

it("exports the ready plan and surfaces export failures", async () => {
  mocks.query={isLoading:false,isError:false,data:{id:7,status:"ready",invented_pdas:false,group:1,campo:"L",grade:"1",theme:"T",proyecto:{}}};
  mocks.export.mockRejectedValue(new Error("export failed"));
  const {host,root}=await mount();
  const exportButton=[...host.querySelectorAll("button")].find((button)=>button.textContent?.includes("Exportar"))!;
  await act(async()=>exportButton.dispatchEvent(new MouseEvent("click",{bubbles:true})));
  expect(mocks.export).toHaveBeenCalledWith(7,"docx"); expect(host.textContent).toContain("export failed");
  await act(async()=>root.unmount());
});

it("shows failed state and redirects after regeneration succeeds", async () => {
  mocks.query={isLoading:false,isError:false,data:{id:7,status:"failed",failure_reason:"detalle",group:1,campo:"L",grade:"1",theme:"T",proyecto:{}}};
  const {host,root}=await mount();
  expect(host.textContent).toContain("La generación falló: detalle");
  await act(async()=>host.querySelector("button")!.dispatchEvent(new MouseEvent("click",{bubbles:true})));
  const [, options]=mocks.mutate.mock.calls[0];
  await act(async()=>options.onSuccess({id:9}));
  expect(mocks.push).toHaveBeenCalledWith("/planeaciones/9");
  await act(async()=>root.unmount());
});
