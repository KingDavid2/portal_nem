"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

/** Fixture-backed campos formativos (backend `lesson_plans/core/pdas.py`'s
 * `available_campos()` — RAG is OFF for this milestone, so generation is
 * only supported for campos with a hardcoded PDA fixture; design.md Open
 * Questions: "gate the campo selector to the fixture-backed campos"). Kept
 * as a literal list here — there is no dedicated endpoint exposing
 * `available_campos()` in this milestone's scope. */
export const AVAILABLE_CAMPOS = [
  "Ética, Naturaleza y Sociedades",
  "Lenguajes",
] as const;

/** Create-generation form for LessonPlan, scoped to the currently selected
 * Group (ai-planeaciones spec — "Generation Request Is Gated, Workspace-
 * Bound, and Schema-Validated"). Submitting enqueues async generation; the
 * caller is responsible for polling the resulting id to `ready`/`failed`. */
export function GenerateForm({
  groupId,
  defaultGrade,
  onSubmit,
  errorMessage,
  isPending,
}: {
  groupId: number;
  defaultGrade?: string;
  onSubmit: (input: { group: number; campo: string; grade: string; theme: string }) => void;
  errorMessage: string | null;
  isPending: boolean;
}) {
  const [campo, setCampo] = useState<string>(AVAILABLE_CAMPOS[0]);
  const [grade, setGrade] = useState(defaultGrade ?? "");
  const [theme, setTheme] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit({ group: groupId, campo, grade, theme });
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 rounded-lg border border-border p-4">
      <h2 className="text-sm font-semibold">Generar planeación</h2>

      <Label className="flex flex-col items-start gap-1">
        <span>Campo formativo</span>
        <select
          value={campo}
          onChange={(event) => setCampo(event.target.value)}
          className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm"
        >
          {AVAILABLE_CAMPOS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </Label>

      <Label className="flex flex-col items-start gap-1">
        <span>Grado</span>
        <Input required value={grade} onChange={(event) => setGrade(event.target.value)} />
      </Label>

      <Label className="flex flex-col items-start gap-1">
        <span>Tema</span>
        <Input required value={theme} onChange={(event) => setTheme(event.target.value)} />
      </Label>

      {errorMessage ? (
        <p className="text-sm text-destructive" role="alert">
          {errorMessage}
        </p>
      ) : null}

      <div className="flex gap-2">
        <Button type="submit" disabled={isPending}>
          {isPending ? "Generando…" : "Generar planeación"}
        </Button>
      </div>
    </form>
  );
}
