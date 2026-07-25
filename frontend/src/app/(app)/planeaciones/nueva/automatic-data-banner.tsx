import type { components } from "@/lib/api/schema";

type CatalogGroup = components["schemas"]["CatalogGroup"];
type CatalogTeacher = components["schemas"]["CatalogTeacher"];

type Props = {
  group: CatalogGroup;
  teacher: CatalogTeacher;
};

/** The four facts the teacher does not get to choose: they follow from the
 * group she picked, so the screen states them instead of asking. Rendered as a
 * tinted band rather than a Card to read as context, not as another form step.
 *
 * `Docente` shows the account email because `User` carries no display name yet
 * — a known gap, tracked in `docs/nueva-planeacion-progress.md`. */
export function AutomaticDataBanner({ group, teacher }: Props) {
  return (
    <div className="rounded-lg border border-primary/15 bg-primary/5 p-4">
      <div className="grid gap-4 sm:grid-cols-4">
        <InfoPair label="Escuela" value={group.school_name} />
        {/* CCT is optional upstream; an empty string would collapse the row. */}
        <InfoPair label="CCT" value={group.school_cct || "—"} />
        <InfoPair label="Ciclo escolar" value={group.school_year_label} />
        <InfoPair label="Docente" value={teacher.email} />
      </div>
    </div>
  );
}

function InfoPair({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[11px] font-semibold uppercase text-muted-foreground">
        {label}
      </span>
      <span className="text-[13px] font-medium text-foreground/80">
        {value}
      </span>
    </div>
  );
}