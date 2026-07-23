import type { Proyecto } from "./proyecto-types";

/** Read-only renderer for a `ready` LessonPlan's ABPC `proyecto` JSON
 * (ai-planeaciones spec — regenerate-only per proposal scope, no in-app
 * partial editing; tasks.md D8.1 "stages → moments → sessions → rubric"). */
export function ProyectoViewer({ proyecto }: { proyecto: Proyecto }) {
  const { datos } = proyecto;

  return (
    <div className="flex flex-col gap-6">
      <section className="flex flex-col gap-1 rounded-lg border border-border p-4">
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
      </section>

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

      <section className="rounded-lg border border-border p-4">
        <h3 className="text-sm font-semibold">Contenidos y PDAs</h3>
        <ul className="mt-2 flex flex-col gap-2 text-sm">
          {proyecto.contents_and_pdas.map((group) => (
            <li key={group.content}>
              <p className="font-medium">{group.content}</p>
              <ul className="ml-4 list-disc">
                {group.pdas.map((pda) => (
                  <li key={pda}>{pda}</li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      </section>

      {proyecto.stages.map((stage) => (
        <section key={stage.name} className="rounded-lg border border-border p-4">
          <h3 className="text-sm font-semibold">Fase: {stage.name}</h3>
          {stage.momentos.map((momento) => (
            <div key={momento.number} className="mt-3">
              <h4 className="text-sm font-medium">
                Momento {momento.number}: {momento.name}
              </h4>
              {momento.sessions.map((session, sessionIdx) => (
                <div key={sessionIdx} className="mt-1 ml-4 text-sm">
                  <p className="text-muted-foreground">
                    Duración: {session.duration_minutes} minutos
                  </p>
                  <ol className="ml-4 list-decimal">
                    {session.steps.map((step) => (
                      <li key={step.number}>{step.dynamic}</li>
                    ))}
                  </ol>
                </div>
              ))}
            </div>
          ))}
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
