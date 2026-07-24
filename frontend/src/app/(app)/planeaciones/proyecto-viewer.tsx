import type { Proyecto } from "./proyecto-types";
import { Card } from "@/components/ui/card";
import { ContenidoCard } from "@/components/ui/contenido-card";
import { MomentoCard } from "@/components/ui/momento-card";

/** Read-only renderer for a `ready` LessonPlan's ABPC `proyecto` JSON
 * (ai-planeaciones spec — regenerate-only per proposal scope, no in-app
 * partial editing; tasks.md D8.1 "stages → moments → sessions → rubric"). */
export function ProyectoViewer({ proyecto }: { proyecto: Proyecto }) {
  const { datos } = proyecto;

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

      <div className="grid gap-3">{proyecto.contents_and_pdas.map((group) => <ContenidoCard key={group.content} title={group.content} pdaRows={group.pdas.map((content) => ({ id: content, content }))} />)}</div>

      {proyecto.stages.map((stage) => (
        <section key={stage.name} className="rounded-lg border border-border p-4">
          <h3 className="text-sm font-semibold">Fase: {stage.name}</h3>
          {stage.momentos.map((momento) => <MomentoCard key={momento.number} title={`Momento ${momento.number}: ${momento.name}`} pasoRows={momento.sessions.flatMap((session) => session.steps.map((step) => ({ number: step.number, content: step.dynamic })))} session={momento.sessions.map((session) => <p key={session.duration_minutes} className="text-sm text-muted-foreground">Duración: {session.duration_minutes} minutos</p>)} />)}
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
