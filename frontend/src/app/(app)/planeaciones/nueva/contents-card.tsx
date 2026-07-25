import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ContenidoCard } from "@/components/ui/contenido-card";
import type { PdaItem } from "@/components/ui/contenido-card";
import type { CatalogContent } from "@/lib/api/lesson-plan-catalog";
import type { ContentSelection } from "./use-new-plan-form";
import { ContentsPicker } from "./contents-picker";

type Props = {
  contents: CatalogContent[];
  selections: ContentSelection[];
  onChange: (selections: ContentSelection[]) => void;
};

/** Card 3 of the Nueva planeación screen: displays the teacher's content
 * selections as read-only content cards and provides a button to open the
 * picker overlay.
 *
 * The picker is a controlled child: `contents-card.tsx` owns the open/closed
 * state and only calls `onChange` after the picker confirms, ensuring the
 * parent's state never changes mid-flight. */
export function ContentsCard({ contents, selections, onChange }: Props) {
  const [pickerOpen, setPickerOpen] = useState(false);

  /** Compute which content_ids have been selected so we can render only
   * their selected PDAs as read-only rows. */
  const selectionSet = new Map<string, Set<string>>();
  for (const s of selections) {
    if (s.pda_ids.length > 0) {
      selectionSet.set(s.content_id, new Set(s.pda_ids));
    }
  }

  const selectedCount = selectionSet.size;
  const pdaCount = selections.reduce((sum, s) => sum + s.pda_ids.length, 0);

  /** PDA rows for a content that has been selected — only show the PDAs
   * the teacher actually picked. */
  function rowsFor(contentId: string): PdaItem[] {
    const ids = selectionSet.get(contentId);
    if (!ids) return [];

    // Find the content object from the catalog to get PDA texts.
    const content = contents.find((c) => c.id === contentId);
    if (!content) return [];

    return content.pdas
      .filter((pda) => ids.has(pda.id))
      .map((pda) => ({
        id: pda.id,
        content: pda.text,
        selected: true,
      }));
  }

  return (
    <>
      <Card className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h2 className="text-base font-semibold">Contenidos y PDAs</h2>
          <p className="text-[13px] text-muted-foreground">
            Texto oficial del programa sintético. La IA no los inventa ni los reescribe.
          </p>
        </div>

        <Button
          variant="outline"
          onClick={() => setPickerOpen(true)}
        >
          Elegir contenidos y PDAs
        </Button>

        {/* Render selected content cards as read-only so the teacher can see
            what's picked without re-interacting with them. */}
        {selections.map((sel) => {
          if (sel.pda_ids.length === 0) return null;
          const content = contents.find((c) => c.id === sel.content_id);
          if (!content) return null;
          return (
            <ContenidoCard
              key={content.id}
              title={content.text}
              readOnly
              pdaRows={rowsFor(content.id)}
            />
          );
        })}

        {/* Footer count — shows the total after filtering out empty selections. */}
        <div className="pt-2">
          <span className="text-xs text-muted-foreground">
            {selectedCount} contenidos · {pdaCount} PDAs seleccionados
          </span>
        </div>
      </Card>

      {/* Picker overlay — only mounted when the teacher has opened it.
          onConfirm fires the change handler and closes the picker; onCancel
          just closes it, discarding the draft. */}
      {pickerOpen && (
        <ContentsPicker
          contents={contents}
          selections={selections}
          onCancel={() => setPickerOpen(false)}
          onConfirm={(next) => {
            onChange(next);
            setPickerOpen(false);
          }}
        />
      )}
    </>
  );
}