import { useEffect, useState, useMemo, useRef } from "react";
import { X } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ContenidoCard } from "@/components/ui/contenido-card";
import type { PdaItem } from "@/components/ui/contenido-card";
import type { CatalogContent } from "@/lib/api/lesson-plan-catalog";
import type { ContentSelection } from "./use-new-plan-form";

/** A content-selection overlay rendered as a fixed-position overlay rather
 * than a native `<dialog>` (jsdom 29 does not implement
 * `HTMLDialogElement.showModal`). The parent's `selections` prop is never
 * mutated directly; editing happens on a local draft that is committed only
 * when the teacher presses "Usar estos contenidos". */
type Props = {
  contents: CatalogContent[];
  selections: ContentSelection[];
  onCancel: () => void;
  onConfirm: (selections: ContentSelection[]) => void;
};

/** Seed the picker's draft from the parent's current selections so the
 * teacher sees existing picks on open. Only non-empty entries survive —
 * the backend rejects empty `pda_ids` arrays. */
function buildDraftMap(selections: ContentSelection[]): Map<string, string[]> {
  const map = new Map<string, string[]>();
  for (const s of selections) {
    if (s.pda_ids.length > 0) {
      map.set(s.content_id, [...s.pda_ids]);
    }
  }
  return map;
}

/** Build a flat lookup from PDA id → content id. Used by `onSelectedChange`
 * inside ContenidoCard: the primitive fires (pdaId, value) but the handler
 * needs to know which content to mutate. */
function buildPdaToContent(contents: CatalogContent[]): Map<string, string> {
  const m = new Map<string, string>();
  for (const c of contents) {
    for (const p of c.pdas) {
      m.set(p.id, c.id);
    }
  }
  return m;
}

export function ContentsPicker({ contents, selections, onCancel, onConfirm }: Props) {
  /** Local draft state: each entry maps content_id → selected PDA ids.
   * The content entry is dropped when the last PDA is unchecked so we
   * never surface an empty array to the backend. */
  const [draftMap, setDraftMap] = useState<Map<string, string[]>>(() => buildDraftMap(selections));
  const [search, setSearch] = useState("");
  const searchRef = useRef<HTMLInputElement>(null);

  /** Close on Escape so keyboard users cannot get trapped in the overlay.
   * One listener per mount; cleanup prevents stale callbacks. */
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onCancel]);

  /** Autofocus the search box on mount so the first keystroke filters. */
  useEffect(() => {
    searchRef.current?.focus();
  }, []);

  /** Filter contents by search string: match content text OR any PDA text,
   * case-insensitive. A content with zero selected PDAs still appears if it
   * matches the query, so the teacher can select from it. */
  const filteredContents = useMemo(() => {
    if (!search.trim()) return contents;
    const q = search.toLowerCase();
    return contents.filter((c) => {
      if (c.text.toLowerCase().includes(q)) return true;
      return c.pdas.some((pda) => pda.text.toLowerCase().includes(q));
    });
  }, [contents, search]);

  /** The `pdaId → contentId` lookup so ContenidoCard's single
   * `onSelectedChange` handler can resolve the parent content for any PDA.
   * Always built from the full catalog so every PDA is accounted for even
   * when the search hides its content card. */
  const pdaToContent = useMemo(() => buildPdaToContent(contents), [contents]);

  /** Every count below is deliberately computed over the WHOLE catalog and the
   * whole draft, never over `filteredContents`. The search box hides rows; it
   * does not deselect them. Counting the visible subset would let a filter
   * silently under-report what "Usar estos contenidos" is about to commit —
   * a teacher who picked four PDAs then typed a query would read
   * "1 PDAs seleccionados" and still commit four. */
  const selectedPdaCount = useMemo(() => {
    let count = 0;
    for (const pdaIds of draftMap.values()) count += pdaIds.length;
    return count;
  }, [draftMap]);

  const totalPdaCount = useMemo(
    () => contents.reduce((total, content) => total + content.pdas.length, 0),
    [contents],
  );

  /** A content counts as selected exactly when it holds at least one PDA —
   * the draft never keeps an empty entry, so its size is the content count. */
  const selectedContentCount = draftMap.size;

  /** PDA rows for a single content card. The `selected` flag is derived from
   * the draft so checkboxes reflect current draft state. */
  function rowsFor(content: CatalogContent): PdaItem[] {
    return content.pdas.map((pda) => ({
      id: pda.id,
      content: pda.text,
      selected: (draftMap.get(content.id)?.includes(pda.id) ?? false),
    }));
  }

  /** When a PDA checkbox is toggled inside a ContenidoCard, update the
   * draft map. Adding a PDA: insert it if not present. Removing the last PDA
   * of a content: delete the whole content entry so the backend never sees
   * an empty `pda_ids` array. */
  function onPdaChange(pdaId: string, checked: boolean) {
    const contentId = pdaToContent.get(pdaId);
    if (!contentId) return; // should never happen but be defensive

    setDraftMap((prev) => {
      const next = new Map(prev);
      const current = [...(next.get(contentId) ?? [])];
      if (checked) {
        if (!current.includes(pdaId)) {
          next.set(contentId, [...current, pdaId]);
        }
      } else {
        const filtered = current.filter((id) => id !== pdaId);
        if (filtered.length === 0) {
          next.delete(contentId);
        } else {
          next.set(contentId, filtered);
        }
      }
      return next;
    });
  }

  /** Select every PDA of every currently-visible content in one action. */
  function selectAll() {
    setDraftMap((prev) => {
      const next = new Map(prev);
      for (const c of filteredContents) {
        next.set(c.id, [...c.pdas.map((p) => p.id)]);
      }
      return next;
    });
  }

  /** Clear all selections across every content. */
  function clearAll() {
    setDraftMap(new Map());
  }

  /** Dismiss only when the scrim itself was clicked. Without the identity
   * check the handler also fires for clicks that bubbled up out of the panel,
   * so ticking a checkbox would close the picker and discard the draft. */
  function dismissOnScrimClick(event: React.MouseEvent<HTMLDivElement>) {
    if (event.target === event.currentTarget) onCancel();
  }

  /** Convert the internal draft map to the ContentSelection[] shape the
   * parent expects on confirm. */
  function toSelections(): ContentSelection[] {
    return [...draftMap.entries()].map(([content_id, pda_ids]) => ({
      content_id,
      pda_ids,
    }));
  }

  /** Empty-state card shown when there are no catalog contents to present.
   * The teacher must pick a field first. */
  if (contents.length === 0) {
    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        onClick={dismissOnScrimClick}
      >
        <Card
          role="dialog"
          aria-modal="true"
          aria-label="Contenidos y PDAs"
          className="mx-4 w-full max-w-lg bg-background p-6"
        >
          <p className="text-center text-sm text-muted-foreground">
            Aún no hay contenidos verificados para este campo.
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 pt-8"
      onClick={dismissOnScrimClick}
    >
      {/* `role="dialog"` belongs on the panel, not the scrim: the scrim is the
          dismiss surface, and naming it the dialog would make the whole
          viewport the dialog's boundary for assistive tech. */}
      <Card
        role="dialog"
        aria-modal="true"
        aria-label="Contenidos y PDAs"
        className="flex h-[85vh] w-full max-w-3xl flex-col gap-0 overflow-hidden bg-background px-4 shadow-2xl sm:mx-0"
      >
        {/* Header: title + counter + close button */}
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h2 className="text-base font-semibold">Contenidos y PDAs</h2>
          <div className="flex items-center gap-3">
            <span className="rounded-md bg-muted px-2 py-1 text-xs font-medium text-muted-foreground">
              {selectedPdaCount} / {totalPdaCount}
            </span>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={onCancel}
            >
              <X className="size-4" />
            </Button>
          </div>
        </div>

        {/* Toolbar: search input + bulk actions */}
        <div className="flex items-center gap-2 border-b px-4 py-2">
          <input
            ref={searchRef}
            type="search"
            placeholder="Buscar contenido o PDA…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-8 w-full rounded-md border border-input bg-background px-3 text-sm outline-none transition-colors focus:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
          />
          <Button variant="outline" size="xs" onClick={selectAll}>
            Seleccionar todos
          </Button>
          <Button variant="outline" size="xs" onClick={clearAll}>
            Limpiar selección
          </Button>
        </div>

        {/* Scrollable list of content cards with their PDA rows */}
        <div className="flex-1 overflow-y-auto px-4 py-3">
          {filteredContents.map((content) => (
            <ContenidoCard
              key={content.id}
              title={content.text}
              selected={(draftMap.get(content.id)?.length ?? 0) > 0}
              onSelectedChange={onPdaChange}
              pdaRows={rowsFor(content)}
            />
          ))}
        </div>

        {/* Footer: count + confirm / cancel buttons */}
        <div className="flex items-center justify-between border-t px-4 py-3">
          <span className="text-xs text-muted-foreground">
            {selectedContentCount} contenidos · {selectedPdaCount} PDAs seleccionados
          </span>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={onCancel}>
              Cancelar
            </Button>
            <Button size="sm" onClick={() => onConfirm(toSelections())}>
              Usar estos contenidos
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}