"use client";

import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ProjectContextCard } from "./project-context-card";
import { AutomaticDataBanner } from "./automatic-data-banner";
import { CrossCuttingThemesCard } from "./cross-cutting-themes-card";
import { ContentsCard } from "./contents-card";
import { useNewPlanForm, validateNewPlanForm, buildCreatePayload } from "./use-new-plan-form";
import { useGroupsQuery } from "@/lib/api/groups";
import { useLessonPlanFieldsQuery, useLessonPlanCatalogQuery, useGenerationQuotaQuery } from "@/lib/api/lesson-plan-catalog";
import { useCreateLessonPlanMutation } from "@/lib/api/lesson-plans";
import { ApiError } from "@/lib/api/errors";
import { SummaryPanel } from "./summary-panel";

/** Reads `?group=<id>` off the URL, or `null` when it is absent or not a
 * number. `/planeaciones` links here carrying whichever group the teacher had
 * filtered to, so the first select arrives pre-answered; a hand-typed or stale
 * URL must degrade to "no group picked" rather than to `NaN`. */
function readGroupIdParam(raw: string | null): number | null {
  if (raw === null || raw.trim() === "") return null;
  const parsed = Number(raw);
  return Number.isInteger(parsed) ? parsed : null;
}

/** The screen proper, split out from the default export so the `Suspense`
 * boundary can sit *above* it. `useSearchParams` opts its subtree into
 * client-side rendering, and a static page that calls it without a boundary
 * fails the production build outright ("Missing Suspense boundary with
 * useSearchParams") — dev renders on demand and hides this, so the boundary
 * cannot be dropped just because the page looks fine locally. */
/** The 429 the server answers with once the month's generations are spent. It
 * is the one create failure a teacher can act on, so it gets its own sentence
 * instead of the serializer-error formatting `ApiError.message` applies. */
function quotaExceededMessage(error: unknown): string | undefined {
  if (!(error instanceof ApiError)) return undefined;
  const body = error.body;
  if (typeof body !== "object" || body === null) return undefined;
  const { code, limit } = body as { code?: unknown; limit?: unknown };
  if (code !== "generation_quota_exceeded" || typeof limit !== "number") {
    return undefined;
  }
  return `Ya usaste tus ${limit} generaciones de este mes. El contador se reinicia el próximo mes.`;
}

function NewPlanFormInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // Read once for the reducer's initial state only — afterwards `state.groupId`
  // is the source of truth, so changing the select does not fight the URL.
  const [state, dispatch] = useNewPlanForm(readGroupIdParam(searchParams.get("group")));
  const groupsQuery = useGroupsQuery();
  const fieldsQuery = useLessonPlanFieldsQuery();
  const catalogQuery = useLessonPlanCatalogQuery(state.groupId, state.fieldId);
  const catalog = catalogQuery.data;
  const quotaQuery = useGenerationQuotaQuery();
  const createMutation = useCreateLessonPlanMutation();

  // `null` whenever the form is not submittable — the CTA reads it directly
  // rather than re-deriving submittability from a second source.
  const payload = catalog ? buildCreatePayload(state, catalog.methodology.id) : null;
  const pendingRequirements = Object.values(validateNewPlanForm(state));

  function handleSubmit() {
    if (payload === null) return;
    createMutation.mutate(payload, {
      onSuccess: (plan) => router.push(`/planeaciones/${plan.id}`),
    });
  }

  const pdaCount = state.selections.reduce(
    (total, selection) => total + selection.pda_ids.length,
    0,
  );

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <span className="text-[13px] font-medium text-primary">Planeaciones</span>
        <h1 className="text-2xl font-semibold tracking-tight">Nueva planeación</h1>
        <p className="text-sm text-muted-foreground">
          Tú defines el contexto y los PDAs. La IA solo secuencia los momentos.
        </p>
      </header>
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="flex flex-col gap-6 lg:col-span-2">
          <ProjectContextCard
            state={state}
            dispatch={dispatch}
            groups={groupsQuery.data ?? []}
            fields={fieldsQuery.data ?? []}
            catalog={catalog}
          />
          {catalog !== undefined && (
            <AutomaticDataBanner group={catalog.group} teacher={catalog.teacher} />
          )}
          {catalog !== undefined && (
            <CrossCuttingThemesCard
              themes={catalog.cross_cutting_themes ?? []}
              selectedIds={state.themeIds}
              onToggle={(themeId) => dispatch({ type: "toggleThemeId", themeId })}
            />
          )}
          {catalog !== undefined && (
            <ContentsCard
              contents={catalog.contents ?? []}
              selections={state.selections}
              onChange={(selections) => dispatch({ type: "setSelections", selections })}
            />
          )}
        </div>
        <SummaryPanel
          methodologyName={catalog?.methodology.name}
          durationWeeks={state.durationWeeks}
          pdaCount={pdaCount}
          ejeCount={state.themeIds.length}
          pendingRequirements={pendingRequirements}
          submitAllowed={payload !== null}
          onSubmit={handleSubmit}
          isPending={createMutation.isPending}
          quota={quotaQuery.data}
          errorMessage={
            createMutation.error
              ? quotaExceededMessage(createMutation.error) ?? createMutation.error.message
              : undefined
          }
        />
      </div>
    </div>
  );
}

export default function Page() {
  // `null` rather than a skeleton: the boundary only covers the search-param
  // read, which resolves in the same tick, so a skeleton would flash.
  return (
    <Suspense fallback={null}>
      <NewPlanFormInner />
    </Suspense>
  );
}