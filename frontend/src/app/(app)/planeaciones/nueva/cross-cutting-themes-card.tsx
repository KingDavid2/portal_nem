import type { CatalogTheme } from "@/lib/api/lesson-plan-catalog";
import { Card } from "@/components/ui/card";
import { ChoiceChip } from "@/components/ui/choice-chip";

type Props = {
  themes: CatalogTheme[];
  selectedIds: string[];
  onToggle: (themeId: string) => void;
};

/** Card 2 of the Nueva planeación screen: the teacher picks the cross-cutting
 * themes (`ejes articuladores`) that frame the project.
 *
 * Themes arrive with the catalog, which only loads once a group *and* a campo
 * formativo are set, so an empty list means "not chosen yet" rather than "this
 * campo has none" — the caption says so instead of rendering a bare card. */
export function CrossCuttingThemesCard({ themes, selectedIds, onToggle }: Props) {
  return (
    <Card className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h2 className="text-base font-semibold">Ejes articuladores</h2>
        <p className="text-[13px] text-muted-foreground">
          {themes.length === 0
            ? "Selecciona un campo formativo para ver sus ejes."
            : "Elige los que atraviesan el proyecto. La IA redacta la justificación de cada uno."}
        </p>
      </div>
      {themes.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {themes.map((theme) => (
            /* `onSelectedChange` reports the *toggled* value, so a selected chip
               fires `false`. The boolean is dropped and the id passed straight
               to the reducer, which owns the set logic — the primitive knows
               nothing about the group of chips around it. */
            <ChoiceChip
              key={theme.id}
              variant="multi"
              selected={selectedIds.includes(theme.id)}
              onSelectedChange={() => onToggle(theme.id)}
            >
              {theme.name}
            </ChoiceChip>
          ))}
        </div>
      )}
    </Card>
  );
}
