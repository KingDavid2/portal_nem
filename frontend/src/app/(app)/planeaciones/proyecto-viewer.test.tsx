import { renderToStaticMarkup } from "react-dom/server"; import { afterEach, describe, expect, it, vi } from "vitest"; import { ProyectoViewer } from "./proyecto-viewer"; import type { Proyecto, ContentPda } from "./proyecto-types";
const proyecto:Proyecto={title:"Proyecto",purpose:"P",problem_or_theme:"T",datos:{school_name:"E",cct:"C",phase:1,grade:"1",campo_formativo:"L",methodology:"M",date:"D"},articulating_axes:[],contents_and_pdas:[{content:"Contenido",pdas:["PDA","PDA"]}],stages:[{name:"Fase",momentos:[{number:1,name:"Inicio",sessions:[{duration_minutes:30,steps:[{number:1,dynamic:"Paso A"},{number:1,dynamic:"Paso B"}]},{duration_minutes:45,steps:[{number:1,dynamic:"Paso C"}]}]},{number:2,name:"Vacío",sessions:[]}]}],rubric:{criteria:[]}};
// Controlled mock that exposes pdaRows props so we can assert on unofficial marks.
vi.mock("@/components/ui/contenido-card",()=>{const MockCard=({title,pdaRows}:{title:string;pdaRows?:{content:React.ReactNode;unofficial?:boolean}[]})=><div data-testid="contenido-card"><h3>{title}</h3>{(pdaRows||[]).map((row,i:number)=> <div key={i} data-testid="pda-row" data-unofficial={row.unofficial?"true":"false"}>{row.content}</div>)}</div>;return{ContenidoCard:MockCard}});
afterEach(()=>vi.restoreAllMocks());describe("ProyectoViewer",()=>{it("keeps sessions, duplicate steps, empty moments, and content read-only",()=>{const error=vi.spyOn(console,"error").mockImplementation(()=>{});const html=renderToStaticMarkup(<ProyectoViewer proyecto={proyecto}/>);expect(html).toContain("Contenidos y PDAs");expect(html).not.toContain('type="checkbox"');expect(html).toMatch(/Sesión 1 · 30 minutos[\s\S]*Paso A[\s\S]*Paso B/);expect(html).toMatch(/Sesión 2 · 45 minutos[\s\S]*Paso C/);expect(html).toMatch(/Momento 2: Vacío[\s\S]*Sin sesiones/);expect(error).not.toHaveBeenCalled();});});

describe("ProyectoViewer grounding", () => {
  const proyectoWithPdAs: Proyecto = {
    ...proyecto,
    contents_and_pdas: [
      {
        content: "Lectura de textos narrativos",
        pdas: ["El alumno lee comprensivamente textos narrativos.", "El alumno inventa algo que no está en el programa."],
      },
    ],
  };

  const groundingSelections: ContentPda[] = [
    {
      content: "Lectura de textos narrativos",
      pdas: ["El alumno lee comprensivamente textos narrativos."],
    },
  ];

  it("marks the invented PDA and leaves its official sibling unmarked", () => {
    const html = renderToStaticMarkup(
      <ProyectoViewer proyecto={proyectoWithPdAs} groundingSelections={groundingSelections} />,
    );

    // Scoped to the contents section: the Fundamentación section below renders
    // the same official text through the same card, always unmarked, so an
    // unscoped assertion would pass on a viewer that marks every content row.
    const contents = html.slice(0, html.indexOf("Fundamentación oficial"));

    expect(contents).toContain(
      '<div data-testid="pda-row" data-unofficial="false">El alumno lee comprensivamente textos narrativos.</div>',
    );
    expect(contents).toContain(
      '<div data-testid="pda-row" data-unofficial="true">El alumno inventa algo que no está en el programa.</div>',
    );
  });

  it("renders the Fundamentación oficial section with selections", () => {
    const html = renderToStaticMarkup(
      <ProyectoViewer proyecto={proyectoWithPdAs} groundingSelections={groundingSelections} />,
    );

    expect(html).toContain("Fundamentación oficial (SEP)");
    expect(html).toContain("Lectura de textos narrativos");
    expect(html).toContain("El alumno lee comprensivamente textos narrativos.");
  });

  it("legacy path: no grounding selections renders no marks and no Fundamentación section", () => {
    const html = renderToStaticMarkup(<ProyectoViewer proyecto={proyectoWithPdAs} />);

    // No unofficial marks on any row
    expect(html).not.toContain('data-unofficial="true"');
    // No Fundamentación section
    expect(html).not.toContain("Fundamentación oficial");
  });

  it("normalization: whitespace and casing differences do not mark PDA as unofficial", () => {
    const proyectoWithWhitespacePdA: Proyecto = {
      ...proyecto,
      contents_and_pdas: [
        {
          content: "Lectura de textos narrativos",
          pdas: ["  EL ALUMNO LEE   comprensivamente  textos narrativos.  "],
        },
      ],
    };

    const html = renderToStaticMarkup(
      <ProyectoViewer proyecto={proyectoWithWhitespacePdA} groundingSelections={groundingSelections} />,
    );

    // Despite whitespace/casing differences, should NOT be marked unofficial
    expect(html).not.toContain('data-unofficial="true"');
    expect(html).toContain("EL ALUMNO LEE   comprensivamente  textos narrativos");
  });
});
