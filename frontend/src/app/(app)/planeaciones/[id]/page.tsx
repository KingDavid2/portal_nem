"use client";

import { use, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatusChip } from "@/components/ui/status-chip";
import {
  lessonPlanCreateInput,
  useCreateLessonPlanMutation,
  useLessonPlanQuery,
} from "@/lib/api/lesson-plans";
import { downloadLessonPlanExport } from "@/lib/api/lesson-plan-export";
import { ProyectoViewer } from "../proyecto-viewer";
import type { Proyecto } from "../proyecto-types";

/** Read-only proyecto viewer + docx export + regenerate (ai-planeaciones
 * spec — "Ready LessonPlan Can Be Exported as Docx or Markdown"; regenerate-
 * only per proposal scope, no in-app partial editing). Completes the
 * exit-gate walkthrough: teacher selects group → generates → polls to ready
 * → views → exports docx. */
export default function PlaneacionViewerPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const planId = Number(id);
  const router = useRouter();

  const planQuery = useLessonPlanQuery(planId);
  const regenerateMutation = useCreateLessonPlanMutation();

  const [exportError, setExportError] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);

  const plan = planQuery.data;

  function handleExport() {
    setExportError(null);
    setIsExporting(true);
    downloadLessonPlanExport(planId, "docx")
      .catch((error: Error) => setExportError(error.message))
      .finally(() => setIsExporting(false));
  }

  // Null for plans created before the catalog contract: their stored context
  // cannot produce a valid create body, so regeneration is not offered.
  const regenerateInput = plan ? lessonPlanCreateInput(plan) : null;

  function handleRegenerate() {
    if (!regenerateInput) return;
    regenerateMutation.mutate(regenerateInput, {
      onSuccess: (newPlan) => router.push(`/planeaciones/${newPlan.id}`),
    });
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Planeación</h1>
        <Link
          href="/planeaciones"
          className="text-sm text-primary underline-offset-4 hover:underline"
        >
          Volver a planeaciones
        </Link>
      </div>

      {planQuery.isLoading ? (
        <p className="text-muted-foreground">Cargando planeación…</p>
      ) : planQuery.isError || !plan ? (
        <p className="text-sm text-destructive" role="alert">
          No se pudo cargar la planeación.
        </p>
      ) : plan.status === "pending" ? (
        <Card className="flex items-center gap-3"><StatusChip tone="brand">Generando</StatusChip><p className="text-muted-foreground">Generando planeación…</p></Card>
      ) : plan.status === "failed" ? (
        <Card className="flex flex-col gap-3">
          <StatusChip tone="danger">Falló</StatusChip>
          <p className="text-sm text-destructive" role="alert">
            La generación falló: {plan.failure_reason || "sin detalle."}
          </p>
          <div>
            <Button onClick={handleRegenerate} disabled={regenerateMutation.isPending || !regenerateInput}>
              {regenerateMutation.isPending ? "Regenerando…" : "Reintentar"}
            </Button>
          </div>
        </Card>
      ) : (
        <>
          {plan.invented_pdas ? (
            <Card
              className="border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"
              role="alert"
            >
              Esta planeación incluye al menos un PDA que no está en el conjunto fuente
              (posible invención del modelo). Revísala antes de usarla.
            </Card>
          ) : null}

          <div className="flex flex-wrap gap-2">
            <Button onClick={handleExport} disabled={isExporting}>
              {isExporting ? "Descargando…" : "Exportar a Word (.docx)"}
            </Button>
            <Button
              variant="outline"
              onClick={handleRegenerate}
              disabled={regenerateMutation.isPending || !regenerateInput}
            >
              {regenerateMutation.isPending ? "Regenerando…" : "Regenerar"}
            </Button>
          </div>

          {exportError ? (
            <p className="text-sm text-destructive" role="alert">
              {exportError}
            </p>
          ) : null}

          <ProyectoViewer proyecto={plan.proyecto as Proyecto} />
        </>
      )}
    </div>
  );
}
