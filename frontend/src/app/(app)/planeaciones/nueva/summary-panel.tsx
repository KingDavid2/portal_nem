import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { GenerationQuota } from "@/lib/api/lesson-plan-catalog";

type Props = {
  methodologyName?: string;
  durationWeeks: number;
  pdaCount: number;
  ejeCount: number;
  /** What still stands between the teacher and a submittable form, in
   * teacher-facing Spanish. Non-empty exactly when `submitAllowed` is false,
   * so the disabled CTA always says why it is disabled. */
  pendingRequirements: string[];
  submitAllowed: boolean;
  onSubmit: () => void;
  isPending: boolean;
  quota?: GenerationQuota;
  errorMessage?: string;
};

/** The ABP Comunitario skeleton is fixed at 3 phases and 11 moments — it is a
 * property of the methodology itself, not of this plan, so it is stated rather
 * than counted. Nothing in the catalog carries it. */
const STRUCTURE_LABEL = "3 fases · 11 momentos";

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <span className="text-[13px] text-muted-foreground">{label}</span>
      <span className="text-sm font-medium">{value}</span>
    </div>
  );
}

/** The right column of the Nueva planeación screen: what the teacher is about
 * to spend a generation on, the CTA, and how many generations the month has
 * left. Purely presentational — the page owns the mutation and decides both
 * `submitAllowed` and `errorMessage`. */
export function SummaryPanel({
  methodologyName,
  durationWeeks,
  pdaCount,
  ejeCount,
  pendingRequirements,
  submitAllowed,
  onSubmit,
  isPending,
  quota,
  errorMessage,
}: Props) {
  return (
    <Card className="flex flex-col gap-4">
      <h2 className="text-base font-semibold">Lo que se va a generar</h2>

      <div className="flex flex-col gap-2">
        <SummaryRow label="Metodología" value={methodologyName ?? "—"} />
        <SummaryRow label="Estructura" value={STRUCTURE_LABEL} />
        <SummaryRow label="Duración" value={`${durationWeeks} semanas`} />
        <SummaryRow label="PDAs" value={`${pdaCount} seleccionados`} />
        <SummaryRow label="Ejes" value={`${ejeCount} seleccionados`} />
      </div>

      <div className="flex flex-col gap-2 text-[13px] text-muted-foreground">
        <p>PDAs, contenidos y ejes se toman tal cual del programa sintético.</p>
        <p>La IA solo redacta los momentos, pasos y dinámicas alrededor de ellos.</p>
        <p>Todo queda editable antes de que lo apruebes.</p>
      </div>

      {/* Stated as remaining steps rather than as errors: the CTA below is
          disabled until they are done, so the teacher can never have submitted
          anything wrong yet — colouring a pristine form red would scold her for
          not having filled a form she just opened. */}
      {pendingRequirements.length > 0 && (
        <div className="flex flex-col gap-1">
          <span className="text-[13px] font-semibold">Falta por completar</span>
          <ul className="flex list-disc flex-col gap-1 pl-5 text-[13px] text-muted-foreground">
            {pendingRequirements.map((requirement) => (
              <li key={requirement}>{requirement}</li>
            ))}
          </ul>
        </div>
      )}

      <Button disabled={!submitAllowed || isPending} onClick={onSubmit}>
        Generar proyecto
      </Button>

      <p className="text-[13px] text-muted-foreground">
        Tarda cerca de un minuto. Puedes salir de esta pantalla: el proyecto se
        sigue generando y te avisamos al terminar.
      </p>

      {errorMessage !== undefined && (
        <p className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
          {errorMessage}
        </p>
      )}

      {quota !== undefined && <QuotaMeter quota={quota} />}
    </Card>
  );
}

function QuotaMeter({ quota }: { quota: GenerationQuota }) {
  // A zero limit is not a real plan, but it would divide to `NaN` and ship
  // `width: NaN%` — clamp it to an empty bar instead of trusting the server.
  const percent = quota.limit > 0 ? Math.min(100, (quota.used / quota.limit) * 100) : 0;

  return (
    <div className="flex flex-col gap-2 border-t pt-4">
      <h3 className="text-[13px] font-semibold">Generaciones de este mes</h3>
      <SummaryRow label="Usadas" value={`${quota.used} de ${quota.limit}`} />
      <div
        role="progressbar"
        aria-valuenow={quota.used}
        aria-valuemin={0}
        aria-valuemax={quota.limit}
        className="h-2 w-full overflow-hidden rounded-full bg-muted"
      >
        <div className="h-full bg-primary" style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}
