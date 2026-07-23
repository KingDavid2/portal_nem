"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { Group } from "@/lib/api/groups";

const GRADO_OPTIONS = [1, 2, 3] as const;

/** Create/edit form for Group, scoped to the currently selected SchoolYear
 * (frontend-foundation spec — "Full CRUD lifecycle for an entity").
 * `school_year` is fixed by the caller, not user-editable here. */
export function GroupForm({
  schoolYearId,
  initial,
  onSubmit,
  onCancel,
  errorMessage,
  isPending,
}: {
  schoolYearId: number;
  initial?: Group;
  onSubmit: (input: { school_year: number; grado: number; grupo: string }) => void;
  onCancel?: () => void;
  errorMessage: string | null;
  isPending: boolean;
}) {
  const [grado, setGrado] = useState<number>(initial?.grado ?? 1);
  const [grupo, setGrupo] = useState(initial?.grupo ?? "");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit({ school_year: schoolYearId, grado, grupo });
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 rounded-lg border border-border p-4">
      <h2 className="text-sm font-semibold">
        {initial ? "Editar grupo" : "Nuevo grupo"}
      </h2>

      <Label className="flex flex-col items-start gap-1">
        <span>Grado</span>
        <select
          value={grado}
          onChange={(event) => setGrado(Number(event.target.value))}
          className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm"
        >
          {GRADO_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </Label>

      <Label className="flex flex-col items-start gap-1">
        <span>Grupo (p. ej. A)</span>
        <Input
          required
          maxLength={1}
          value={grupo}
          onChange={(event) => setGrupo(event.target.value.toUpperCase())}
        />
      </Label>

      {errorMessage ? (
        <p className="text-sm text-destructive" role="alert">
          {errorMessage}
        </p>
      ) : null}

      <div className="flex gap-2">
        <Button type="submit" disabled={isPending}>
          {isPending ? "Guardando…" : initial ? "Guardar cambios" : "Crear grupo"}
        </Button>
        {onCancel ? (
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancelar
          </Button>
        ) : null}
      </div>
    </form>
  );
}
