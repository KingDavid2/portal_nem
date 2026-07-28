import type { ContentPda, Proyecto } from "./proyecto-types";
import { Card } from "@/components/ui/card";
import { ContenidoCard } from "@/components/ui/contenido-card";
import { MomentoCard } from "@/components/ui/momento-card";

/** Normalize PDA text for comparison — mirrors backend grounding.py rule. */
function normalizePda(text: string): string {
  return text.replace(/\s+/g, " ").trim().toLocaleLowerCase();
}

/** Read-only renderer for a `ready` LessonPlan's ABPC `proyecto` JSON
 * (ai-planeaciones spec — regenerate-only per proposal scope, no in-app
 * partial editing; tasks.md D8.1 "stages → moments → sessions → rubric"). */
export function ProyectoViewer({
  proyecto,
  groundingSelections,
}: {
  proyecto: Proyecto;
  groundingSelections?: ContentPda[];
}) {
  const { datos } = proyecto;

  // Built once, outside the render loop. A plan with no snapshot was never
  // checked against anything, so it gets no marks at all — an empty set would
  // mark every row of a legacy plan as outside a selection that never existed.
  const hasGrounding = groundingSelections != null && groundingSelections.length > 0;
  const officialPdas = hasGrounding
    ? new Set(groundingSelections.flatMap((g) => g.pdas.map(normalizePda)))
    : null;

  return (
    <div className="flex flex-col gap-6">
      <Card className="flex flex-col gap-1">
        <h2 className="text-lg font-semibold">{proyecto.title}</h2>
        <p className="text-sm text-muted-foreground">
          {datos.school_name} · {datos.cct} · Fase {datos.phase} · Grado {datos.grade}
        </p>
        <p className="text-sm text-muted-foreground">
          Campo formativo: {datos.campo_formativo} · Metodología: {datos.methodology} · {datos.date}
        </p>
        <p className="mt-2 text-sm">
          <span className="font-medium">Problemática o tema: </span>
          {proyecto.problem_or_theme}
        </p>
        <p className="text-sm">
          <span className="font-medium">Propósito: </span>
          {proyecto.purpose}
        </p>
      </Card>

      <section className="rounded-lg border border-border p-4">
        <h3 className="text-sm font-semibold">Ejes articuladores</h3>
        <ul className="mt-2 flex flex-col gap-1 text-sm">
          {proyecto.articulating_axes.map((axis) => (
            <li key={axis.name}>
              <span className="font-medium">{axis.name}: </span>
              {axis.justification}
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h3 className="text-sm font-semibold">Contenidos y PDAs</h3>
        {proyecto.contents_and_pdas.length === 0 ? (
          <p className="mt-2 text-sm text-muted-foreground">Sin contenidos ni PDAs</p>
        ) : (
          <div className="mt-2 grid gap-3">
            {proyecto.contents_and_pdas.map((group, index) => (
              <ContenidoCard
                key={`${group.content}-${index}`}
                readOnly
                title={group.content}
                pdaRows={group.pdas.map((content, pdaIndex) => ({
                  id: `${index}-${pdaIndex}`,
                  content,
                  unofficial:
                    officialPdas != null && !officialPdas.has(normalizePda(content)),
                }))}
              />
            ))}
          </div>
        )}
      </section>

      {hasGrounding ? (
        <section>
          <h3 className="text-sm font-semibold">Fundamentación oficial (SEP)</h3>
          <div className="mt-2 grid gap-3">
            {groundingSelections.map((selection, index) => (
              <ContenidoCard
                key={`${selection.content}-${index}`}
                readOnly
                title={selection.content}
                pdaRows={selection.pdas.map((pda, pdaIndex) => ({
                  id: `grounding-${index}-${pdaIndex}`,
                  content: pda,
                }))}
              />
            ))}
          </div>
        </section>
      ) : null}

      {proyecto.stages.map((stage) => (
        <section key={stage.name} className="rounded-lg border border-border p-4">
          <h3 className="text-sm font-semibold">Fase: {stage.name}</h3>
          {stage.momentos.map((momento, momentoIndex) => momento.sessions.length === 0 ? <MomentoCard key={`${momento.number}-${momentoIndex}`} title={`Momento ${momento.number}: ${momento.name}`} /> : momento.sessions.map((session, sessionIndex) => <MomentoCard key={`${momento.number}-${momentoIndex}-${sessionIndex}`} title={`Momento ${momento.number}: ${momento.name}`} hasSession subtitle={`Sesión ${sessionIndex + 1} · ${session.duration_minutes} minutos`} pasoRows={session.steps.map((step, stepIndex) => ({ id: `${momentoIndex}-${sessionIndex}-${step.number}-${stepIndex}`, number: step.number, content: step.dynamic }))} />))}
        </section>
      ))}

      <section className="rounded-lg border border-border p-4">
        <h3 className="text-sm font-semibold">Rúbrica de evaluación</h3>
        <ul className="mt-2 flex flex-col gap-1 text-sm">
          {proyecto.rubric.criteria.map((criterion) => (
            <li key={criterion.criterion}>
              <span className="font-medium">{criterion.criterion}: </span>
              {criterion.levels.join(" | ")}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
