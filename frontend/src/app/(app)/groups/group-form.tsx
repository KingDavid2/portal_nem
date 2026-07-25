"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { FormField } from "@/components/ui/form-field";
import { Select } from "@/components/ui/select";
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
    <Card className="p-0"><form onSubmit={handleSubmit} className="flex flex-col gap-4 p-5">
      <h2 className="text-sm font-semibold">
        {initial ? "Editar grupo" : "Nuevo grupo"}
      </h2>

      <FormField id="group-grade" label="Grado"><Select id="group-grade" value={grado} onChange={(event) => setGrado(Number(event.target.value))}>{GRADO_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}</Select></FormField>
      <FormField id="group-name" label="Grupo (p. ej. A)" required><Input id="group-name" required maxLength={1} value={grupo} onChange={(event) => setGrupo(event.target.value.toUpperCase())} /></FormField>

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
    </form></Card>
  );
}
