import { Sparkles } from "lucide-react";

/**
 * Quizzy chat surface — empty state from `designs/quizzy.pen` screen «1 · Vacío».
 * Conversational tools (P4 MCP) land here later; this route exists so the
 * sidebar entry from the design is reachable today.
 */
export default function QuizzyPage() {
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-2xl flex-col items-center justify-center gap-4 text-center">
      <div className="flex size-14 items-center justify-center rounded-full bg-primary/10 text-primary">
        <Sparkles aria-hidden className="size-7" />
      </div>
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          Pregunta sobre tus planeaciones
        </h1>
        <p className="text-sm text-muted-foreground">
          Quizzy responde únicamente con contenidos y PDAs del catálogo oficial
          que seleccionaste. Cada respuesta indica su origen.
        </p>
      </div>
      <p className="text-xs text-muted-foreground">
        Asistente de planeación · fundamentado en el catálogo oficial
      </p>
    </div>
  );
}
