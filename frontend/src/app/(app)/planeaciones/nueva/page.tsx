"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { ProjectContextCard } from "./project-context-card";
import { AutomaticDataBanner } from "./automatic-data-banner";
import { useNewPlanForm } from "./use-new-plan-form";
import { useGroupsQuery } from "@/lib/api/groups";
import { useLessonPlanFieldsQuery, useLessonPlanCatalogQuery } from "@/lib/api/lesson-plan-catalog";

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
function NewPlanFormInner() {
  const searchParams = useSearchParams();
  // Read once for the reducer's initial state only — afterwards `state.groupId`
  // is the source of truth, so changing the select does not fight the URL.
  const [state, dispatch] = useNewPlanForm(readGroupIdParam(searchParams.get("group")));
  const groupsQuery = useGroupsQuery();
  const fieldsQuery = useLessonPlanFieldsQuery();
  const catalogQuery = useLessonPlanCatalogQuery(state.groupId, state.fieldId);
  const catalog = catalogQuery.data;

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
        </div>
        {/* Ejes, contenidos and the "Lo que se va a generar" panel land in the
            next two units; the empty column holds the two-thirds grid now so
            the context card does not reflow when they arrive. */}
        <div />
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